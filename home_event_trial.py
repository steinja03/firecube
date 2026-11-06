"""Bounded PC-assisted Home event trial. No on-device daemon or settings writes."""
from datetime import datetime
import json
from pathlib import Path
from queue import Queue, Empty, Full
import re
import secrets
import subprocess
import threading
import time
from zipfile import ZipFile, ZIP_DEFLATED

from inventory import run

TARGET = 'dev.firecube.launcher/.MainActivity'
FINGERPRINT = 'Amazon/full_tank/tank:5.1.1/LVY48F/288.6.8.8_user_688806320:user/release-keys'
HOMES = {'com.amazon.tv.launcher/.ui.HomeActivity_vNext',
         'com.amazon.tv.launcher/.ui.HomeActivity',
         'com.amazon.tv.launcher/com.amazon.tv.launcher.ui.HomeActivity_vNext',
         'com.amazon.tv.launcher/com.amazon.tv.launcher.ui.HomeActivity'}


def home_event(line):
    match = re.search(r'\bam_resume_activity\s*:\s*\[([^\]]+)\]\s*$', line)
    if not match:
        return False
    fields = [field.strip() for field in match[1].split(',')]
    return len(fields) == 4 and fields[0] == '0' and fields[3] in HOMES


def resumed_component(text):
    lines = [line for line in text.splitlines() if 'mResumedActivity' in line]
    if len(lines) != 1:
        return None
    match = re.search(r'\bu0\s+([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)', lines[0])
    return match[1] if match else None


def wait_for_firecube(foreground, attempts=24):
    observations = []
    for attempt in range(attempts):
        current = foreground()
        if not observations or observations[-1] != current:
            observations.append(current)
        if current in (TARGET, 'dev.firecube.launcher/dev.firecube.launcher.MainActivity'):
            return True, observations
        if attempt + 1 < attempts:
            time.sleep(0.25)
    return False, observations


class Redirector:
    def __init__(self, foreground, launch, record, now=time.monotonic):
        self.foreground, self.launch, self.record, self.now = foreground, launch, record, now
        self.count = 0
        self.last = float('-inf')

    def handle(self, line):
        if not home_event(line):
            return False
        if self.foreground() not in HOMES:
            self.record('ignored_home_event', reason='Amazon Home is no longer foreground')
            return False
        now = self.now()
        if now - self.last < 1.5:
            raise RuntimeError('Home returned too quickly; stopping to avoid a redirect loop')
        if self.count >= 8:
            raise RuntimeError('Eight-redirect trial limit reached')
        self.count += 1
        self.last = now
        self.record('redirect_intent', target=TARGET, number=self.count)
        self.launch()
        self.record('redirect_requested', number=self.count)
        return True


def check_device(adb, serial):
    if run(adb, serial, 'get-state') != 'device':
        raise RuntimeError('Device not connected')
    for key, expected in [('ro.product.device', 'tank'), ('ro.build.version.sdk', '22'),
                          ('ro.build.fingerprint', FINGERPRINT)]:
        if run(adb, serial, 'shell', 'getprop', key) != expected:
            raise RuntimeError('This trial requires the inspected tank/API22/build 688806320')
    users = run(adb, serial, 'shell', 'pm', 'list', 'users')
    if re.findall(r'UserInfo\{(\d+):[^\n]*\}\s+running', users) != ['0']:
        raise RuntimeError('Expected only user 0 running')


def trial(adb, serial, record):
    check_device(adb, serial)
    last_snapshot = [None]
    def foreground():
        text = run(adb, serial, 'shell', 'dumpsys', 'activity', 'activities')
        lines = [line.strip()[:1000] for line in text.splitlines() if 'mResumedActivity' in line][:8]
        if lines != last_snapshot[0]:
            record('foreground_snapshot', resumed_lines=lines)
            last_snapshot[0] = lines
        return resumed_component(text)
    def launch():
        output = run(adb, serial, 'shell', 'am', 'start', '--user', '0', '-n', TARGET, '-f', '0x10200000')
        record('explicit_launch_result', output=output[:2000])
    record('scope', settings_written=False, packages_disabled=False, installed_apps=False,
           device_background_service=False, pc_connection_required=True, duration_seconds=90)
    # Explicit opening proves availability only; it is never counted as Home success.
    launch()
    seen, observations = wait_for_firecube(foreground)
    record('initial_launch_observation', firecube_foreground=seen, foreground_transitions=observations)
    if not seen:
        raise RuntimeError('Firecube foreground not verified after 24 checks; Home test not started')
    lines = Queue(maxsize=4096)
    overflow = threading.Event()
    marker = secrets.token_hex(16)
    process = subprocess.Popen([adb, '-s', serial, 'shell', 'logcat', '-b', 'main', '-b', 'events',
        '-v', 'threadtime', 'am_resume_activity:I', 'FirecubeEventTrial:I', '*:S'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    def read():
        try:
            for line in process.stdout:
                try:
                    lines.put_nowait(line)
                except Full:
                    overflow.set()
                    break
        finally:
            try:
                lines.put_nowait(None)
            except Full:
                overflow.set()
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        run(adb, serial, 'shell', 'log', '-p', 'i', '-t', 'FirecubeEventTrial', marker)
        ready_by = time.monotonic() + 12
        while True:
            if overflow.is_set():
                raise RuntimeError('Event queue overflow; no Home key injected')
            if time.monotonic() >= ready_by:
                raise RuntimeError('Fresh log marker not observed; no Home key injected')
            try:
                line = lines.get(timeout=0.2)
            except Empty:
                continue
            if line is None:
                raise RuntimeError('Log stream closed before readiness')
            if re.search(r'\bFirecubeEventTrial\s*:\s*' + re.escape(marker) + r'\s*$', line):
                break
        record('fresh_stream_ready')
        redirector = Redirector(foreground, launch, record)
        record('home_key_intent', keycode=3)
        run(adb, serial, 'shell', 'input', 'keyevent', '3')
        started = time.monotonic()
        automatic_passed = False
        while time.monotonic() - started < 90:
            if overflow.is_set():
                raise RuntimeError('Event queue overflow; monitor stopped')
            if not automatic_passed and time.monotonic() - started > 15:
                raise RuntimeError('No verified event-triggered Home redirect within 15 seconds')
            try:
                line = lines.get(timeout=0.2)
            except Empty:
                continue
            if line is None:
                raise RuntimeError('Log stream closed; monitor stopped')
            if redirector.handle(line):
                seen, observations = wait_for_firecube(foreground)
                record('redirect_observation', firecube_foreground=seen, number=redirector.count,
                       foreground_transitions=observations)
                if not seen:
                    raise RuntimeError('Launch request did not put Firecube in foreground')
                if not automatic_passed:
                    automatic_passed = True
                    record('automatic_home_test_passed')
                    print('Automatic Home redirect verified. For the remaining trial, open a streaming app and press remote Home.')
                    print('This monitor stops automatically after about 90 seconds. Keep this window open.')
        record('complete', automatic_home_verified=automatic_passed, redirects=redirector.count,
               physical_remote_verified=False, reboot_persistence=False)
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        reader.join(timeout=2)
        process.stdout.close()
        record('pc_logcat_client_stopped', returncode=process.returncode,
               device_daemon_installed=False, persistent_settings_written=False)


def main():
    root = Path(__file__).resolve().parent
    print('PC-ASSISTED HOME EVENT TRIAL — 90 seconds, up to eight redirects.')
    print('Requires a connected PC. No root, app installation, package disabling or settings writes.')
    print('Opens Firecube, injects Home once, and redirects only observed user-0 Amazon Home resumes.')
    default = Path.home() / 'Downloads/platform-tools-latest-windows/platform-tools/adb.exe'
    value = input(f'Official adb.exe path [Enter for {default}]: ').strip().strip('"')
    adb = Path(value) if value else default
    if not adb.is_file():
        raise SystemExit('ADB not found')
    serial = input('Stick identifier [Enter for 192.168.50.39:5555]: ').strip() or '192.168.50.39:5555'
    if any(c.isspace() for c in serial) or serial.startswith('-'):
        raise SystemExit('Invalid device identifier')
    if input('Type TEST HOME EVENTS to start: ').strip() != 'TEST HOME EVENTS':
        return 1
    result = {'exit_code': 0, 'endpoint': serial}
    records = []
    def record(event, **fields):
        records.append({'time': datetime.now().astimezone().isoformat(), 'event': event, **fields})
    try:
        trial(str(adb), serial, record)
    except KeyboardInterrupt:
        result.update(exit_code=1, error='Stopped by user')
    except Exception as error:
        result.update(exit_code=1, error=str(error))
        print('Stopped:', error)
    bundle = root / ('home-events-result-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.zip')
    with ZipFile(bundle, 'x', ZIP_DEFLATED) as archive:
        archive.writestr('result.json', json.dumps(result, indent=2))
        archive.writestr('audit.jsonl', ''.join(json.dumps(row) + '\n' for row in records))
    print('Result:', bundle)
    print('Automatic monitoring has ended. Normal Amazon Home behavior is expected afterward.')
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
