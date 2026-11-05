"""Windows entry point for the scoped preferred-Home trial and rollback."""
from datetime import datetime
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from acceptance import screenshot
from inventory import run
from home_preference_trial import run_trial, restore_trial, BACKUP_PATTERN
import re


def main():
    root = Path(__file__).resolve().parent
    restoring = "--restore" in sys.argv[1:]
    print("PREFERRED HOME ONLY — no package disabling, accessibility activation, root or firmware writes.")
    print("This trial sets Firecube as the saved Home preference only if no prior Home/Firecube defaults exist.")
    print("It saves a device-bound backup, verifies the setting, injects Home once, and checks the foreground.")
    print("Failure triggers a scoped rollback attempt; rollback can fail and is reported explicitly.")
    default = Path.home() / "Downloads/platform-tools-latest-windows/platform-tools/adb.exe"
    value = input(f"Official adb.exe path [Enter for {default}]: ").strip().strip('"')
    adb = Path(value) if value else default
    if not adb.is_file():
        raise SystemExit("ADB not found; stopped")
    serial = input("Stick identifier [Enter for 192.168.50.39:5555]: ").strip() or "192.168.50.39:5555"
    if any(character.isspace() for character in serial):
        raise SystemExit("Invalid identifier")
    phrase = "RESTORE ORIGINAL HOME" if restoring else "SET FIRECUBE HOME"
    original = None
    pointer = root / "homepref-last-trial.txt"
    if restoring:
        default_receipt = pointer.read_text().strip() if pointer.exists() else ""
        original = input(f"Original trial audit [Enter for {default_receipt or 'no default'}]: ").strip().strip('"') or default_receipt
        if not original or not Path(original).is_file():
            raise SystemExit("Original audit not found; stopped")
    print("The target is dev.firecube.launcher/.MainActivity for user 0.")
    print("Restoration clears only the newly-created Firecube Home default, after checking for unrelated preferences.")
    if input(f"Type {phrase} to approve: ").strip() != phrase:
        print("Cancelled; no ADB operations performed.")
        return 1
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    audit = root / (("homepref-restore-" if restoring else "homepref-trial-") + stamp + ".jsonl")
    payload = root / "firecube-home-preference-tool-0.1.0.apk"
    result = {"restoring": restoring, "endpoint": serial, "exit_code": 0}
    backup = None
    try:
        if restoring:
            backup = restore_trial(str(adb), serial, payload, original, audit)
        else:
            backup = run_trial(str(adb), serial, payload, audit,
                on_apply_ready=lambda: pointer.write_text(str(audit)))
    except Exception as error:
        result["exit_code"] = 1
        result["error"] = str(error)
        print("Stopped:", error)
    if audit.exists() and audit.stat().st_size:
        records = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines() if line.strip()]
        baselines = [record for record in records if record.get("event") == "baseline"]
        if baselines:
            backup = baselines[0].get("remote_backup")
    pulled = None
    if backup and re.fullmatch(BACKUP_PATTERN, backup):
        pulled = root / ("homepref-device-backup-" + stamp + ".json")
        try:
            run(str(adb), serial, "pull", backup, str(pulled))
        except Exception as error:
            result["backup_pull_error"] = str(error)
    screen = None
    try:
        screen = screenshot(str(adb), serial)
    except Exception as error:
        result["screenshot_error"] = str(error)
    bundle = root / ("homepref-result-" + stamp + ".zip")
    with ZipFile(bundle, "x", ZIP_DEFLATED) as archive:
        archive.writestr("result.json", json.dumps(result, indent=2))
        if audit.exists():
            archive.write(audit, "audit.jsonl")
        if pulled and pulled.exists():
            archive.write(pulled, "device-backup.json")
        if screen:
            archive.writestr("current-screen.png", screen)
    print(f"Result: {bundle}")
    print("Keep the audit, homepref-last-trial.txt and device backup for Restore-Original-Home.cmd.")
    print("Review device identifiers and visible screen content before sharing the result ZIP.")
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
