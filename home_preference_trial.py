"""Preferred-Home-only trial using a guarded shell payload; no app-state changes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from inventory import run

PAYLOAD_SHA256 = "5a34d9b807b86cdf792c07a5c77d20919bd850ec1e95e4eddf2ef3fa0b8834db"
REMOTE = "/data/local/tmp/firecube-home-preference-tool.apk"
TARGET = "dev.firecube.launcher/.MainActivity"
BACKUP_PATTERN = r"/data/local/tmp/firecube-homepref-backup-[0-9a-f]{16}\.json"


@contextmanager
def journal(path):
    with Path(path).open("x", encoding="utf-8") as stream:
        def record(event, **fields):
            stream.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}) + "\n")
            stream.flush(); os.fsync(stream.fileno())
        yield record


def identity(adb, serial):
    running = run(adb, serial, "shell", "pm", "list", "users")
    if re.findall(r"UserInfo\{(\d+):[^\n]*\}\s+running", running) != ["0"]:
        raise RuntimeError("Expected only user 0 running")
    value = {key: run(adb, serial, "shell", "getprop", key) for key in
             ("ro.product.device", "ro.build.fingerprint", "ro.serialno")}
    if value["ro.product.device"] != "tank" or value["ro.serialno"] in ("", "unknown", "null"):
        raise RuntimeError("Unknown device identity")
    return value


def prepare(adb, serial, payload):
    payload = Path(payload)
    if hashlib.sha256(payload.read_bytes()).hexdigest() != PAYLOAD_SHA256:
        raise RuntimeError("Tool checksum mismatch; not executed")
    run(adb, serial, "push", str(payload.resolve()), REMOTE)
    with tempfile.TemporaryDirectory(prefix="firecube-homepref-check-") as folder:
        copy = Path(folder) / "tool.apk"
        run(adb, serial, "pull", REMOTE, str(copy))
        if hashlib.sha256(copy.read_bytes()).hexdigest() != PAYLOAD_SHA256:
            raise RuntimeError("Transferred tool checksum mismatch")


def native(adb, serial, mode, backup=None):
    if mode not in ("inspect", "apply", "restore"):
        raise ValueError("Unknown mode")
    arguments = ["shell", "CLASSPATH=" + REMOTE, "app_process", "/system/bin",
                 "dev.firecube.homepref.HomePreferenceTool", mode]
    if mode != "inspect":
        if not backup or not re.fullmatch(BACKUP_PATTERN, backup):
            raise ValueError("Invalid backup path")
        arguments.append(backup)
    output = run(adb, serial, *arguments)
    lines = [line for line in output.splitlines() if line.lstrip().startswith("{")]
    if len(lines) != 1:
        raise RuntimeError("No unambiguous tool result")
    result = json.loads(lines[0])
    if result.get("uid") != 2000 or result.get("mode") != mode:
        raise RuntimeError("Unexpected tool identity or mode")
    return result


def accessibility(adb, serial):
    return {key: run(adb, serial, "shell", "settings", "--user", "0", "get", "secure", key)
            for key in ("enabled_accessibility_services", "accessibility_enabled")}


def run_trial(adb, serial, payload, audit_path, on_apply_ready=None):
    remote_backup = "/data/local/tmp/firecube-homepref-backup-" + uuid.uuid4().hex[:16] + ".json"
    with journal(audit_path) as record:
        before_identity = identity(adb, serial)
        before_accessibility = accessibility(adb, serial)
        prepare(adb, serial, payload)
        before = native(adb, serial, "inspect")
        record("baseline", serial=serial, identity=before_identity, remote_backup=remote_backup,
               inspection=before, accessibility=before_accessibility)
        if before.get("ok") is not True:
            raise RuntimeError("Native inspection failed; no Home preference attempted")
        state = before["state"]
        if state.get("preferred") is not None or state.get("home_preferences") or state.get("own_preference_count") != 0:
            raise RuntimeError("Existing Home/Firecube preferences; refusing to overwrite defaults")
        if state.get("permission") != 0 or state.get("target_enabled") is not True:
            raise RuntimeError("Required permission or enabled Firecube candidate missing")
        attempted = False
        try:
            if identity(adb, serial) != before_identity:
                raise RuntimeError("Device changed before mutation")
            record("preferred_home_intent", target=TARGET, user=0, remote_backup=remote_backup)
            if on_apply_ready:
                on_apply_ready()
            attempted = True
            outcome = native(adb, serial, "apply", remote_backup)
            record("preferred_home_result", result=outcome)
            if outcome.get("ok") is not True or outcome.get("preference_observed") is not True:
                rollback = outcome.get("rollback")
                if isinstance(rollback, dict) or outcome.get("rollback_attempted") is True:
                    record("rollback_verified" if isinstance(rollback, dict) and rollback.get("restored") is True else "rollback_unverified", result=rollback)
                    attempted = False  # Native tool already attempted its scoped rollback; do not loop it.
                elif outcome.get("backup_written") is not True and outcome.get("mutation_attempted") is not True:
                    attempted = False
                raise RuntimeError(outcome.get("error") or "Preferred Home did not take effect")
            if identity(adb, serial) != before_identity:
                raise RuntimeError("Device changed before the Home-key test")
            record("home_key_test_intent", injected_keycode=3)
            run(adb, serial, "shell", "input", "keyevent", "3")
            seen = False
            lines = []
            for attempt in range(6):
                text = run(adb, serial, "shell", "dumpsys", "activity", "activities")
                lines = [line.strip() for line in text.splitlines() if "mResumedActivity" in line]
                seen = len(lines) == 1 and "dev.firecube.launcher/" in lines[0]
                if seen:
                    break
                if attempt < 5:
                    time.sleep(1)
            record("home_key_observation", resumed=lines, firecube_seen=seen)
            if not seen:
                raise RuntimeError("Preference was recorded, but the injected Home event did not show Firecube")
            inspected = native(adb, serial, "inspect")
            record("post_home_inspection", result=inspected)
            state_after = inspected.get("state", {})
            if inspected.get("ok") is not True or state_after.get("resolved") != TARGET or state_after.get("own_exact_home_count") != 1:
                raise RuntimeError("Home preference did not remain verified after the injected Home event")
            after_accessibility = accessibility(adb, serial)
            record("complete", preferred_home_observed=True, injected_home_key_firecube_seen=True,
                   physical_remote_and_reboot_verified=False, stock_launcher_disabled=False,
                   alexa_changed=False, accessibility_readbacks_unchanged=(before_accessibility == after_accessibility))
            return remote_backup
        except Exception as error:
            record("stopped", error=str(error))
            if attempted:
                try:
                    if identity(adb, serial) != before_identity:
                        raise RuntimeError("Wrong device for rollback")
                    record("rollback_intent", remote_backup=remote_backup, target=TARGET)
                    result = native(adb, serial, "restore", remote_backup)
                    record("rollback_verified" if result.get("ok") is True else "rollback_unverified", result=result)
                except Exception as rollback_error:
                    record("rollback_unverified", error=str(rollback_error))
            raise


def restore_trial(adb, serial, payload, original_audit, restore_audit):
    source = Path(original_audit)
    if source.stat().st_size > 1024 * 1024:
        raise RuntimeError("Original audit exceeds 1 MB")
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    baselines = [record for record in records if record.get("event") == "baseline"]
    if len(baselines) != 1:
        raise RuntimeError("Expected one original baseline")
    baseline = baselines[0]
    backup = baseline.get("remote_backup", "")
    if not re.fullmatch(BACKUP_PATTERN, backup):
        raise RuntimeError("Invalid original backup path")
    with journal(restore_audit) as record:
        if identity(adb, serial) != baseline["identity"]:
            raise RuntimeError("Wrong device; restore refused")
        prepare(adb, serial, payload)
        record("restore_intent", remote_backup=backup, target=TARGET)
        result = native(adb, serial, "restore", backup)
        record("rollback_verified" if result.get("ok") is True else "rollback_unverified", result=result)
        if result.get("ok") is not True:
            raise RuntimeError("Original Home preference state was not verified restored")
        return backup
