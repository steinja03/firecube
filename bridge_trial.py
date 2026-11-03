"""Reversible, opt-in Home bridge trial. Never disables or uninstalls packages."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import time

from inventory import run, package_names

PACKAGE = "dev.firecube.homebridge"
COMPONENT = PACKAGE + "/.HomeBridgeService"
SERVICES = "enabled_accessibility_services"
ENABLED = "accessibility_enabled"
APK_SHA256 = "60062c776df6e662921b533355cc9999754a790736565105a3f585a5e4d9ecbd"


def service_ids(value):
    if value in ("", "null"):
        return []
    parts = value.split(":")
    if any(not re.fullmatch(r"[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+", part) for part in parts):
        raise RuntimeError("Unexpected accessibility-service value; no settings changed")
    return parts


def normalize(component):
    package, name = component.split("/", 1)
    return package + "/" + (package + name if name.startswith(".") else name)


def read_setting(adb, serial, key):
    return run(adb, serial, "shell", "settings", "--user", "0", "get", "secure", key)


def snapshot(adb, serial):
    if run(adb, serial, "shell", "getprop", "ro.product.device") != "tank":
        raise RuntimeError("This trial is scoped to the user's tank Stick")
    users = run(adb, serial, "shell", "pm", "list", "users")
    running = re.findall(r"UserInfo\{(\d+):[^\n]*\}\s+running", users)
    if running != ["0"]:
        raise RuntimeError("Cannot establish that only user 0 is running; stopped")
    identity = run(adb, serial, "shell", "getprop", "ro.serialno")
    if identity in ("", "unknown", "null"):
        identity = read_setting(adb, serial, "android_id")
    if identity in ("", "unknown", "null"):
        raise RuntimeError("No stable device identifier; stopped before changes")
    fingerprint = run(adb, serial, "shell", "getprop", "ro.build.fingerprint")
    if not fingerprint:
        raise RuntimeError("No device fingerprint")
    services = read_setting(adb, serial, SERVICES)
    service_ids(services)
    enabled = read_setting(adb, serial, ENABLED)
    if enabled not in ("0", "1", "null", ""):
        raise RuntimeError("Unexpected accessibility enabled flag")
    return {"device_identity": identity, "fingerprint": fingerprint,
            "settings": {SERVICES: services, ENABLED: enabled}}


def planned_settings(before):
    values = before["settings"]
    services = service_ids(values[SERVICES])
    if services and values[ENABLED] != "1":
        raise RuntimeError("Other services are configured while accessibility is off; enabling it could activate them. No changes applied.")
    if normalize(COMPONENT) in {normalize(value) for value in services}:
        raise RuntimeError("Bridge is already listed; inspect or restore the previous trial first")
    return {SERVICES: ":".join(services + [COMPONENT]), ENABLED: "1"}


def same_device(before, current):
    return all(before[key] == current[key] for key in ("device_identity", "fingerprint"))


@contextmanager
def journal(path):
    with Path(path).open("x", encoding="utf-8") as stream:
        def record(event, **fields):
            stream.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        yield record


def write_setting(adb, serial, key, value, record):
    if key not in (SERVICES, ENABLED):
        raise RuntimeError("Setting is outside this trial's scope")
    if key == SERVICES:
        service_ids(value)
    elif value not in ("0", "1", "null", ""):
        raise RuntimeError("Invalid enabled flag")
    if value == "null":
        args = ["shell", "settings", "--user", "0", "delete", "secure", key]
    else:
        # ADB's remote shell joins arguments; quote the value to preserve $ in inner-class names.
        args = ["shell", "settings", "--user", "0", "put", "secure", key, shlex.quote(value)]
    record("setting_intent", arguments=args)
    output = run(adb, serial, *args)
    actual = read_setting(adb, serial, key)
    if actual != value:
        raise RuntimeError(f"Setting readback failed for {key}")
    record("setting_verified", key=key, value=actual, output=output)


def set_paused(adb, serial, record, paused):
    args = ["shell", "am", "broadcast", "--user", "0", "--include-stopped-packages",
            "-n", PACKAGE + "/.BridgeControlReceiver", "-a", PACKAGE + ".SET_PAUSED",
            "--ez", "paused", "true" if paused else "false"]
    record("pause_intent" if paused else "resume_intent", arguments=args)
    output = run(adb, serial, *args)
    if not re.search(r"Broadcast completed:\s*result=1\b", output):
        raise RuntimeError("Bridge did not confirm its pause preference")
    record("pause_verified", paused=paused)


def pause(adb, serial, record):
    set_paused(adb, serial, record, True)


def restore_settings(adb, serial, before, planned, record):
    current = snapshot(adb, serial)
    if not same_device(before, current):
        raise RuntimeError("Device identity changed; no restore writes attempted")
    for key in (SERVICES, ENABLED):
        if current["settings"][key] not in (before["settings"][key], planned[key]):
            raise RuntimeError("Accessibility settings changed outside this trial; refusing to overwrite them")
    for key in (SERVICES, ENABLED):
        if current["settings"][key] != before["settings"][key]:
            write_setting(adb, serial, key, before["settings"][key], record)
    after = snapshot(adb, serial)
    if not same_device(before, after) or after["settings"] != before["settings"]:
        raise RuntimeError("Exact settings restoration not verified")
    record("settings_restored", settings=after["settings"])


def apply_trial(adb, serial, apk, receipt):
    apk = Path(apk).resolve()
    if hashlib.sha256(apk.read_bytes()).hexdigest() != APK_SHA256:
        raise RuntimeError("APK checksum mismatch; nothing installed")
    with journal(receipt) as record:
        before = snapshot(adb, serial)
        planned = planned_settings(before)
        installed_packages = package_names(run(adb, serial, "shell", "pm", "list", "packages", "dev.firecube.launcher"))
        if "dev.firecube.launcher" not in installed_packages:
            raise RuntimeError("Firecube launcher is not installed; no changes applied")
        record("baseline", serial=serial, before=before, planned=planned)
        installed = False
        settings_attempted = False
        try:
            record("install_intent", apk=apk.name, sha256=APK_SHA256, package=PACKAGE)
            result = run(adb, serial, "install", "-r", str(apk))
            if "Success" not in result.splitlines():
                raise RuntimeError("Installation did not report Success")
            installed = True
            record("installed", package=PACKAGE)
            pause(adb, serial, record)
            current = snapshot(adb, serial)
            if not same_device(before, current) or current["settings"] != before["settings"]:
                raise RuntimeError("Device or settings changed during installation")
            settings_attempted = True
            for key in (SERVICES, ENABLED):
                if planned[key] != before["settings"][key]:
                    write_setting(adb, serial, key, planned[key], record)
            set_paused(adb, serial, record, False)
            time.sleep(2)
            record("home_test_intent", keycode=3)
            run(adb, serial, "shell", "input", "keyevent", "3")
            observed = False
            lines = []
            for attempt in range(6):
                activity = run(adb, serial, "shell", "dumpsys", "activity", "activities")
                lines = [line.strip() for line in activity.splitlines() if "mResumedActivity" in line]
                observed = len(lines) == 1 and "dev.firecube.launcher/" in lines[0]
                if observed:
                    break
                if attempt < 5:
                    time.sleep(1)
            record("home_observation", resumed_activity=lines, firecube_seen=observed)
            if not observed:
                raise RuntimeError("Trial did not observe Firecube after Home; attempting settings rollback")
            record("complete", home_redirect_observed=True, stock_launcher_disabled=False,
                   alexa_changed=False, reboot_behavior_verified=False)
        except Exception as error:
            record("failed", error=str(error))
            # Pause only our app, and restore only the two saved settings after identity checks.
            if installed:
                try:
                    current = snapshot(adb, serial)
                    if not same_device(before, current):
                        raise RuntimeError("Cannot verify original device for rollback")
                    pause(adb, serial, record)
                    if settings_attempted:
                        restore_settings(adb, serial, before, planned, record)
                    record("rollback_complete", bridge_apk_left_installed_and_paused=True)
                except Exception as rollback_error:
                    record("rollback_unverified", error=str(rollback_error))
                    raise RuntimeError(f"{error}; rollback unverified: {rollback_error}. Inspect the receipt.") from error
            raise


def restore_trial(adb, serial, receipt, restore_audit):
    path = Path(receipt)
    if path.stat().st_size > 1024 * 1024:
        raise RuntimeError("Receipt too large")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    baselines = [record for record in records if record.get("event") == "baseline"]
    if len(baselines) != 1:
        raise RuntimeError("Expected one baseline record")
    before = baselines[0]["before"]
    planned = planned_settings(before)
    with journal(restore_audit) as record:
        current = snapshot(adb, serial)
        if not same_device(before, current):
            raise RuntimeError("Wrong device; no restore writes attempted")
        pause(adb, serial, record)
        restore_settings(adb, serial, before, planned, record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--apk", type=Path, default=Path(__file__).with_name("firecube-home-bridge-0.1.0-debug.apk"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    receipt = args.receipt or Path("bridge-trial-" + stamp + ".jsonl")
    print("Scoped to tank, user 0. No root, firmware writes, package disabling or uninstalls.")
    print("Trial installs our paused bridge, saves both accessibility settings, adds only its service,")
    print("enables accessibility, resumes the bridge, presses Home once and observes the foreground.")
    print("On failure it attempts a scoped settings rollback, preserving concurrent changes.")
    print("The bridge can reveal Amazon home briefly and leaves it running. Alexa remains unchanged.")
    if not args.apply:
        print("Preview only. Nothing executed. Add --apply for an explicitly confirmed trial or rollback.")
        return
    phrase = "RESTORE BRIDGE" if args.restore else "ENABLE BRIDGE"
    if input(f"Type {phrase} to approve: ").strip() != phrase:
        parser.exit(1, "Cancelled; nothing changed.\n")
    try:
        if args.restore:
            restore_trial(args.adb, args.serial, args.restore, receipt)
        else:
            apply_trial(args.adb, args.serial, args.apk, receipt)
    except Exception as error:
        parser.exit(1, f"Stopped: {error}\nReceipt, if created: {receipt}\n")
    print(f"Completed. Keep and share the receipt: {receipt}")


if __name__ == "__main__":
    main()
