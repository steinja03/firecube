"""Start/status/stop controls for a current-boot, shell-UID Home observer."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from zipfile import ZipFile, ZIP_DEFLATED

from inventory import run
from home_event_trial import check_device, resumed_component, wait_for_firecube, TARGET

PAYLOAD_SHA256 = '40db5bee9d9c4da344ce6c5eca1fc854cd4eeeaff533b12be1f0a82aec18b11f'
BOOT_HELPER_SHA256 = '53c722edd023d5b4d735dfba0c0249984de39395e42f69264a7bcb1cd27f9e82'
REMOTE = '/data/local/tmp/firecube-shell-observer-0.1.0.apk'
ROOT = '/data/local/tmp/firecube-observer'
ENTRY = 'dev.firecube.observer.ShellObserver'
SCRIPT = ("#!/system/bin/sh\ntrap '' HUP\nCLASSPATH=" + REMOTE + ' app_process /system/bin ' + ENTRY +
          ' serve </dev/null >' + ROOT + '/console.log 2>&1 &\n')


def stage(adb, serial, payload):
    payload = Path(payload)
    if hashlib.sha256(payload.read_bytes()).hexdigest() != PAYLOAD_SHA256:
        raise RuntimeError('Observer tool checksum mismatch')
    # Stage under a different inode; never truncate code a running observer may map.
    staging = REMOTE + '.stage'
    run(adb, serial, 'push', str(payload.resolve()), staging)
    with tempfile.TemporaryDirectory(prefix='firecube-observer-check-') as folder:
        copy = Path(folder) / 'observer.apk'
        run(adb, serial, 'pull', staging, str(copy))
        if hashlib.sha256(copy.read_bytes()).hexdigest() != PAYLOAD_SHA256:
            raise RuntimeError('Transferred observer checksum mismatch')
    run(adb, serial, 'shell', 'mv', staging, REMOTE)


def native(adb, serial, mode):
    if mode not in ('status', 'stop'):
        raise ValueError('Unapproved observer control command')
    output = run(adb, serial, 'shell', 'CLASSPATH=' + REMOTE, 'app_process', '/system/bin', ENTRY, mode)
    lines = [line for line in output.splitlines() if line.lstrip().startswith('{')]
    if len(lines) != 1:
        raise RuntimeError('No unambiguous observer result')
    value = json.loads(lines[0])
    if value.get('ok') is not True or value.get('uid') != 2000 or value.get('mode') != mode:
        raise RuntimeError('Observer query failed: ' + str(value.get('error', 'Unexpected identity/mode')))
    return value


def status(adb, serial):
    return native(adb, serial, 'status')['status']


def ready(value):
    snapshot = value.get('snapshot') or {}
    return value.get('alive') is True and snapshot.get('state') == 'monitoring' and snapshot.get('ready') is True


def stop(adb, serial, record):
    record('stop_intent')
    native(adb, serial, 'stop')
    for _ in range(30):
        value = status(adb, serial)
        if value.get('alive') is False:
            record('stop_verified', status=value)
            return value
        time.sleep(0.5)
    record('stop_unverified', status=value)
    raise RuntimeError('Observer stop not verified; retain this report')


def start(adb, serial, record):
    before = status(adb, serial)
    record('before_start', status=before)
    if before.get('alive') is True:
        if not ready(before):
            raise RuntimeError('An observer exists but is not ready; use Stop and review its status')
        record('already_running', status=before)
        return before  # Do not inject keys into an existing session on a repeat Start.
    old_session = (before.get('snapshot') or {}).get('session')
    launched = False
    try:
        # Native status has validated/created the private, shell-owned runtime directory.
        with tempfile.TemporaryDirectory(prefix='firecube-observer-start-') as folder:
            script = Path(folder) / 'start.sh'
            script.write_bytes(SCRIPT.encode('ascii'))
            run(adb, serial, 'push', str(script), ROOT + '/start.sh')
        record('detached_start_intent', current_boot_only=True, root=False)
        launched = True
        run(adb, serial, 'shell', 'sh', ROOT + '/start.sh')
        for _ in range(40):
            value = status(adb, serial)
            if ready(value) and value['snapshot'].get('session') != old_session:
                break
            if value.get('alive') is False and (value.get('snapshot') or {}).get('session') != old_session:
                raise RuntimeError('Observer exited during startup: ' + str(value))
            time.sleep(0.5)
        else:
            raise RuntimeError('Observer readiness not verified')
        record('detached_observer_ready', status=value)
        # Establish Firecube availability without calling this a Home test.
        launch_output = run(adb, serial, 'shell', 'am', 'start', '--user', '0', '-n', TARGET, '-f', '0x10200000')
        record('explicit_launch_result', output=launch_output[:2000])
        def foreground():
            return resumed_component(run(adb, serial, 'shell', 'dumpsys', 'activity', 'activities'))
        seen, observations = wait_for_firecube(foreground)
        record('initial_foreground', verified=seen, transitions=observations)
        if not seen:
            raise RuntimeError('Firecube foreground not verified')
        # Flush old events before taking a redirect counter baseline.
        time.sleep(1)
        base = status(adb, serial)
        if not ready(base):
            raise RuntimeError('Observer lost readiness before Home test')
        count = base['snapshot']['redirects']
        record('home_key_test_intent', previous_redirect_count=count)
        run(adb, serial, 'shell', 'input', 'keyevent', '3')
        for _ in range(40):
            value = status(adb, serial)
            snapshot = value.get('snapshot') or {}
            if not value.get('alive'):
                raise RuntimeError('Observer exited during Home test: ' + str(value))
            if ready(value) and snapshot.get('redirects', 0) > count:
                seen, observations = wait_for_firecube(foreground)
                if seen:
                    record('device_home_test_verified', status=value, transitions=observations,
                           pc_disconnect_verified=False, reboot_autostart=False, alexa_changed=False)
                    return value
            time.sleep(0.5)
        raise RuntimeError('Device-side Home redirection not verified')
    except Exception:
        if launched:
            try:
                stop(adb, serial, record)
            except Exception as error:
                record('recovery_unverified', error=str(error))
        raise
    except KeyboardInterrupt:
        if launched:
            try:
                stop(adb, serial, record)
            except Exception as error:
                record('recovery_unverified', error=str(error))
        raise



def install_boot_helper(adb, serial, apk, record):
    apk = Path(apk)
    if hashlib.sha256(apk.read_bytes()).hexdigest() != BOOT_HELPER_SHA256:
        raise RuntimeError('Boot helper checksum mismatch')
    if not ready(status(adb, serial)):
        raise RuntimeError('Start and verify the device observer before installing its boot helper')
    record('boot_helper_install_intent', package='dev.firecube.boothelper', user=0,
           permissions=['INTERNET', 'RECEIVE_BOOT_COMPLETED'], boot_start_default=False)
    output = run(adb, serial, 'install', '--user', '0', '-r', str(apk.resolve()))
    if 'Success' not in output.split():
        raise RuntimeError('Boot helper installation did not report success')
    paths = run(adb, serial, 'shell', 'pm', 'path', 'dev.firecube.boothelper').splitlines()
    if len(paths) != 1 or not paths[0].startswith('package:/'):
        raise RuntimeError('Installed boot helper path not verified')
    with tempfile.TemporaryDirectory(prefix='firecube-boot-helper-check-') as folder:
        installed = Path(folder) / 'installed.apk'
        run(adb, serial, 'pull', paths[0][8:], str(installed))
        if hashlib.sha256(installed.read_bytes()).hexdigest() != BOOT_HELPER_SHA256:
            raise RuntimeError('Installed boot helper hash mismatch')
    record('boot_helper_install_verified', package='dev.firecube.boothelper')
    run(adb, serial, 'shell', 'am', 'start', '--user', '0', '-n', 'dev.firecube.boothelper/.ControllerActivity')
    return {'installed_verified': True, 'local_adb_pairing_verified': False, 'reboot_autostart_verified': False}

def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    if mode not in ('start', 'status', 'stop', 'install-boot-helper'):
        raise SystemExit('Usage: observer_control.py start|status|stop|install-boot-helper')
    root = Path(__file__).resolve().parent
    print('FIRECUBE DEVICE-SIDE OBSERVER — no root or firmware changes.')
    print('Start runs a shell observer on the Stick, opens Firecube and tests Home once.')
    print('It can continue after PC disconnect if the detached launch survives on this firmware.')
    print('Reboot ends the shell session unless the optional paired boot helper successfully restarts it.')
    print('Alexa is unchanged. Local boot-helper pairing and reboot behavior require device testing.')
    if mode == 'install-boot-helper':
        print('Installs a controller with network and boot permissions. It connects only to local ADB.')
        print('Pairing is a separate on-TV approval granting this helper ADB shell access. Boot start defaults off.')
    default = Path.home() / 'Downloads/platform-tools-latest-windows/platform-tools/adb.exe'
    value = input(f'Official adb.exe path [Enter for {default}]: ').strip().strip('"')
    adb = Path(value) if value else default
    if not adb.is_file():
        raise SystemExit('ADB not found')
    serial = input('Stick identifier [Enter for 192.168.50.39:5555]: ').strip() or '192.168.50.39:5555'
    if any(c.isspace() for c in serial) or serial.startswith('-'):
        raise SystemExit('Invalid identifier')
    phrase = {'start': 'START DEVICE OBSERVER', 'stop': 'STOP DEVICE OBSERVER',
              'install-boot-helper': 'INSTALL LOCAL BOOT HELPER'}.get(mode)
    if phrase and input(f'Type {phrase} to proceed: ').strip() != phrase:
        return 1
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    audit = root / ('observer-' + mode + '-' + stamp + '.jsonl')
    result = {'mode': mode, 'exit_code': 0, 'endpoint': serial}
    with audit.open('x', encoding='utf-8') as stream:
        def record(event, **fields):
            stream.write(json.dumps({'time': datetime.now().astimezone().isoformat(), 'event': event, **fields}) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        device_verified = False
        tool_verified = False
        try:
            check_device(str(adb), serial)
            device_verified = True
            stage(str(adb), serial, root / 'firecube-shell-observer-0.1.0.apk')
            tool_verified = True
            if mode == 'start':
                value = start(str(adb), serial, record)
                print('Device-side Home test passed, or a ready session already exists.')
                print('Next: close the PC ADB session or disconnect its network; test Home from streaming apps.')
                print('Do not reboot for this test. Reconnect and run Observer-Status.cmd to collect evidence.')
            elif mode == 'stop':
                value = stop(str(adb), serial, record)
                print('Observer stopped for this boot. Amazon Home behavior is expected.')
                print('If boot start was enabled in the TV controller, turn it off there before rebooting.')
            elif mode == 'install-boot-helper':
                value = install_boot_helper(str(adb), serial, root / 'firecube-boot-helper-0.1.0.apk', record)
                print('On TV: open Pair / Start and authorize its local ADB key if prompted.')
                print('After success, enable boot start explicitly. Then perform the documented reboot test.')
            else:
                value = status(str(adb), serial)
                record('status', status=value)
                print(json.dumps(value, indent=2))
            result['status'] = value
        except (Exception, KeyboardInterrupt) as error:
            result.update(exit_code=1, error=str(error) or 'Interrupted by user')
            record('stopped_with_error', error=result['error'])
            print('Stopped:', result['error'])
        if device_verified and tool_verified:
            try:
                record('final_native_status', status=status(str(adb), serial))
            except Exception as error:
                record('final_status_unavailable', error=str(error))
            try:
                record('observer_console', output=run(str(adb), serial, 'shell', 'cat', ROOT + '/console.log')[:8192])
            except Exception as error:
                record('console_unavailable', error=str(error))
    bundle = root / ('observer-result-' + mode + '-' + stamp + '.zip')
    with ZipFile(bundle, 'x', ZIP_DEFLATED) as archive:
        archive.writestr('result.json', json.dumps(result, indent=2))
        archive.write(audit, 'audit.jsonl')
    print('Report:', bundle)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
