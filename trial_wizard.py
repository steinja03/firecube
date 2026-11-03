"""Interactive Windows-friendly entry point and one-result-bundle collector."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from acceptance import screenshot
from inventory import run


def main():
    root = Path(__file__).resolve().parent
    restoring = "--restore" in sys.argv[1:]
    default_adb = Path.home() / "Downloads/platform-tools-latest-windows/platform-tools/adb.exe"
    print("Firecube Home Bridge — reversible experimental trial, not root or launcher removal.")
    answer = input(f"Official adb.exe path [Enter for {default_adb}]: ").strip().strip('"')
    adb = Path(answer) if answer else default_adb
    if not adb.is_file():
        raise SystemExit("ADB not found. Nothing changed.")
    serial = input("Stick identifier [Enter for 192.168.50.39:5555]: ").strip() or "192.168.50.39:5555"
    if not serial or any(c.isspace() for c in serial):
        raise SystemExit("Invalid identifier. Nothing changed.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    receipt = root / ("bridge-restore-" if restoring else "bridge-trial-")
    receipt = receipt.with_name(receipt.name + stamp + ".jsonl")
    args = [sys.executable, str(root / "bridge_trial.py"), "--adb", str(adb),
            "--serial", serial, "--receipt", str(receipt), "--apply"]
    if restoring:
        previous_file = root / "bridge-last-receipt.txt"
        default = previous_file.read_text().strip() if previous_file.exists() else ""
        previous = input(f"Original trial receipt [Enter for {default or 'no default'}]: ").strip().strip('"') or default
        if not previous or not Path(previous).is_file():
            raise SystemExit("Original receipt not found. Nothing changed.")
        args += ["--restore", previous]
    else:
        args += ["--apk", str(root / "firecube-home-bridge-0.1.0-debug.apk")]
    print("If ADB is disconnected, reconnect in platform-tools first; approve only your own device prompt.")
    code = subprocess.call(args)
    if not receipt.exists() or not receipt.stat().st_size:
        print("No device-change receipt was created. Review the error or cancellation above.")
        return code
    if not restoring:
        (root / "bridge-last-receipt.txt").write_text(str(receipt))
    evidence = {"trial_exit_code": code, "serial": serial, "experimental": True, "restoring": restoring}
    for key, command in {
        "incremental": ["getprop", "ro.build.version.incremental"],
        "kernel": ["cat", "/proc/version"],
        "accessibility": ["dumpsys", "accessibility"],
        "bridge_package": ["dumpsys", "package", "dev.firecube.homebridge"],
        "shell_permissions": ["dumpsys", "package", "com.android.shell"],
        "bootloader_reported": ["getprop", "ro.bootloader"],
        "verified_boot_reported": ["getprop", "ro.boot.verifiedbootstate"],
    }.items():
        try:
            evidence[key] = {"ok": True, "output": run(str(adb), serial, "shell", *command)}
        except Exception as error:
            evidence[key] = {"ok": False, "error": str(error)}
    screen = None
    try:
        screen = screenshot(str(adb), serial)
    except Exception as error:
        evidence["screenshot_error"] = str(error)
    bundle = root / ("bridge-result-" + stamp + ".zip")
    with ZipFile(bundle, "x", ZIP_DEFLATED) as archive:
        archive.write(receipt, "receipt.jsonl")
        archive.writestr("evidence.json", json.dumps(evidence, indent=2))
        if screen:
            archive.writestr("current-screen.png", screen)
    print(f"Result bundle: {bundle}")
    print("Review device identifiers, accessibility metadata and the screenshot before sharing this ZIP.")
    print("Keep the original receipt. Restore-Home-Bridge.cmd uses it to restore the saved settings.")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
