"""Explicitly approved disable/enable test of dev.firecube.probe ONLY.

Never disables a streaming app, Amazon package or launcher. The disposable probe
may finish explicitly enabled even if its initial state was default-enabled.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from inventory import run

PACKAGE = "dev.firecube.probe"


def state(adb, serial):
    text = run(adb, serial, "shell", "dumpsys", "package", PACKAGE)
    matches = re.findall(r"(?m)^\s*User 0:\s*(.*)$", text)
    if len(matches) != 1 or not re.search(r"\binstalled=true\b", matches[0]):
        raise RuntimeError("Probe is not verifiably installed for user 0")
    value = re.search(r"\benabled=([0-4])\b", matches[0])
    if not value:
        raise RuntimeError("Cannot read probe enabled override")
    return int(value[1])


def test_probe(adb, serial, journal_path):
    """Caller must obtain consent before invocation. Exclusive durable journal."""
    with Path(journal_path).open("x", encoding="utf-8") as journal:
        def record(event, **fields):
            journal.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(),
                                      "event": event, **fields}) + "\n")
            journal.flush()
            os.fsync(journal.fileno())

        record("start", device=serial, package=PACKAGE, user=0)
        fingerprint = None
        before = None
        operation = None
        try:
            fingerprint = run(adb, serial, "shell", "getprop", "ro.build.fingerprint")
            if not fingerprint:
                raise RuntimeError("Device fingerprint unavailable")
            before = state(adb, serial)
            if before not in (0, 1):
                raise RuntimeError("Probe must start enabled; no changes applied")
            record("baseline", fingerprint=fingerprint, original_override=before)
            for operation, expected in (("disable-user", 3), ("enable", 1)):
                # Write intent before each mutation, and stop if recording fails.
                args = ["shell", "pm", operation, "--user", "0", PACKAGE]
                if run(adb, serial, "shell", "getprop", "ro.build.fingerprint") != fingerprint:
                    raise RuntimeError("Device fingerprint changed; stopped")
                record("command_intent", arguments=args)
                output = run(adb, serial, *args)
                actual = state(adb, serial)
                record("verification", operation=operation, output=output, override=actual)
                if actual != expected:
                    raise RuntimeError(f"{operation} state verification failed; stopped")
            record("complete", probe_disable_enable_verified=True,
                   original_override_restored=(before == 1),
                   system_package_permission_verified=False,
                   stock_launcher_recovery_verified=False)
        except Exception as error:
            after = None
            check_error = None
            # Read only: do not attempt an automatic repair after a failed mutation.
            # Avoid attributing another device's state to this test after reconnection.
            try:
                if not fingerprint or run(adb, serial, "shell", "getprop", "ro.build.fingerprint") != fingerprint:
                    raise RuntimeError("Device identity could not be reverified")
                after = state(adb, serial)
            except Exception as verification_error:
                check_error = str(verification_error)
            denied = "SecurityException" in str(error) or "Permission Denial" in str(error)
            recovery = ([adb, "-s", serial, "shell", "pm", "enable", "--user", "0", PACKAGE]
                        if after in (2, 3, 4) else None)
            unchanged = before is not None and after == before
            record("stopped", error=str(error), blocked_operation=operation,
                   permission_denied=denied, final_override=after,
                   original_override_unchanged=unchanged, final_state_read_error=check_error,
                   recovery_preview=recovery)
            if unchanged:
                observation = f"Final probe override is {after}, matching its original state. No recovery change is indicated."
            elif after in (0, 1):
                observation = f"Final probe override is {after} (default/explicit enabled); exact original override may differ."
            elif recovery:
                observation = f"Probe is verified disabled (override {after}). Inspect the audit's probe-only recovery preview; permission may still be denied."
            else:
                observation = "Final probe state could not be verified. Inspect the audit before any recovery operation."
            raise RuntimeError(f"{error}\n{observation}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for operation in ("disable-user", "enable"):
        print([args.adb, "-s", args.serial, "shell", "pm", operation, "--user", "0", PACKAGE])
    print("Only the disposable probe changes. Final state is explicitly enabled, not necessarily its original default override.")
    if not args.apply:
        print("Preview only. Nothing executed.")
        return
    if input("Type TEST PROBE to approve these two changes: ").strip() != "TEST PROBE":
        parser.exit(1, "Cancelled; nothing changed.\n")
    try:
        test_probe(args.adb, args.serial, args.journal)
    except Exception as error:
        parser.exit(1, f"Test stopped: {error}. Inspect the journal before recovery.\n")
    print("Probe disable/enable verified. This does not authorize disabling system packages.")


if __name__ == "__main__":
    main()
