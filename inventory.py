"""Read-only ADB inventory. Uses Python 3.10+ and official Android platform-tools."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


PROPERTIES = (
    "ro.product.model", "ro.product.device", "ro.build.version.name",
    "ro.build.version.release", "ro.build.version.sdk", "ro.build.display.id",
    "ro.build.fingerprint",
)


def package_names(output):
    names = set()
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if not re.fullmatch(r"package:[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", line):
            raise ValueError(f"Unexpected package-list output: {line}")
        names.add(line.removeprefix("package:"))
    return names


def run(adb, serial, *arguments):
    result = subprocess.run(
        [adb, "-s", serial, *arguments], capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=45,
    )
    if result.returncode or result.stderr.strip():
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ADB failed")
    output = result.stdout.strip()
    if re.search(r"(?im)^(error:|error\b|exception|securityexception|/system/bin/sh:)", output):
        raise RuntimeError(output)
    return output


def collect(adb, serial):
    def shell(*args):
        return run(adb, serial, "shell", *args)

    if run(adb, serial, "get-state") != "device":
        raise RuntimeError("Selected device is not ready")
    properties = {key: shell("getprop", key) for key in PROPERTIES}
    identity = shell("id")
    all_packages = package_names(shell("pm", "list", "packages"))
    system = package_names(shell("pm", "list", "packages", "-s"))
    disabled = package_names(shell("pm", "list", "packages", "-d"))
    enabled = package_names(shell("pm", "list", "packages", "-e"))
    if not all_packages or system - all_packages or disabled - all_packages or enabled - all_packages:
        raise RuntimeError("Inconsistent inventory; no backup written. Retry when package activity stops.")
    if enabled & disabled or enabled | disabled != all_packages:
        raise RuntimeError("Could not verify enabled states; no backup written.")
    if shell("getprop", "ro.build.fingerprint") != properties["ro.build.fingerprint"]:
        raise RuntimeError("Device fingerprint changed during collection")
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "adb_serial": serial,
        "properties": properties,
        "shell_identity": identity,
        "read_only": True,
        "backup_scope": "Observed package enabled states; not app data, APKs, or a firmware backup",
        "restoration_verified": False,
        "packages": [
            {"package": name, "system": name in system,
             "enabled": name in enabled, "label": None, "version": None,
             "dependencies": None, "risk": "unknown", "description": None,
             "restorable": None}
            for name in sorted(all_packages)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb", help="Path to adb.exe")
    parser.add_argument("--serial", required=True, help="Exact device identifier from adb devices -l")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = collect(args.adb, args.serial)
        # Exclusive creation preserves previous baselines rather than overwriting them.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Inventory stopped: {error}\n")
    print(f"Saved {len(report['packages'])} packages to {args.output}")


if __name__ == "__main__":
    main()
