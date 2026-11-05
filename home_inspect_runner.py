"""Query-only Home API inspector. Pushes a temporary DEX container; never installs it."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from inventory import run

PAYLOAD_SHA256 = "07eb38e44c1fbbd295a15f52dbbbaf1e582c6c77146fc8c786199f14d02c0140"
REMOTE = "/data/local/tmp/firecube-readonly-home-inspector.apk"


def inspect(adb, serial, payload):
    payload = Path(payload)
    if hashlib.sha256(payload.read_bytes()).hexdigest() != PAYLOAD_SHA256:
        raise RuntimeError("Inspector checksum mismatch; nothing copied or executed")
    if run(adb, serial, "shell", "getprop", "ro.product.device") != "tank":
        raise RuntimeError("Inspector is scoped to tank")
    if run(adb, serial, "shell", "getprop", "ro.build.version.sdk") != "22":
        raise RuntimeError("Inspector is scoped to API 22")
    keys = ("enabled_accessibility_services", "accessibility_enabled")
    before = {key: run(adb, serial, "shell", "settings", "--user", "0", "get", "secure", key) for key in keys}
    # Copy and read back only our temporary container; no package install occurs.
    run(adb, serial, "push", str(payload.resolve()), REMOTE)
    with tempfile.TemporaryDirectory(prefix="firecube-inspector-check-") as folder:
        copy = Path(folder) / "inspector.apk"
        run(adb, serial, "pull", REMOTE, str(copy))
        if hashlib.sha256(copy.read_bytes()).hexdigest() != PAYLOAD_SHA256:
            raise RuntimeError("Transferred inspector hash mismatch; not executed")
    output = run(adb, serial, "shell", "CLASSPATH=" + REMOTE, "app_process", "/system/bin",
                 "dev.firecube.inspect.HomeInspector", "inspect")
    lines = [line for line in output.splitlines() if line.lstrip().startswith("{")]
    if len(lines) != 1:
        raise RuntimeError("No unambiguous inspector JSON result")
    result = json.loads(lines[0])
    if result.get("read_only") is not True or result.get("mode") != "inspect" or result.get("uid") != 2000:
        raise RuntimeError("Unexpected inspector mode or UID")
    after = {key: run(adb, serial, "shell", "settings", "--user", "0", "get", "secure", key) for key in keys}
    return {"inspector": result, "accessibility_before": before, "accessibility_after": after,
            "accessibility_readbacks_unchanged": before == after,
            "mutating_package_manager_methods_invoked": False,
            "temporary_container": REMOTE}


def main():
    root = Path(__file__).resolve().parent
    print("Read-only Home API inspection: no app installs, Home presses, setting writes, root or firmware changes.")
    print("Copies a checksum-verified inspector to /data/local/tmp and invokes query methods as ADB shell.")
    default = Path.home() / "Downloads/platform-tools-latest-windows/platform-tools/adb.exe"
    value = input(f"Official adb.exe path [Enter for {default}]: ").strip().strip('"')
    adb = Path(value) if value else default
    if not adb.is_file():
        raise SystemExit("ADB not found. Nothing changed.")
    serial = input("Stick identifier [Enter for 192.168.50.39:5555]: ").strip() or "192.168.50.39:5555"
    if any(character.isspace() for character in serial):
        raise SystemExit("Invalid identifier")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    try:
        result = inspect(str(adb), serial, root / "firecube-home-inspector-0.1.0.apk")
    except Exception as error:
        result = {"collection_failed": True, "error": str(error), "package_installs_or_settings_writes_attempted": False}
    result["endpoint"] = serial
    bundle = root / ("home-inspection-" + stamp + ".zip")
    with ZipFile(bundle, "x", ZIP_DEFLATED) as archive:
        archive.writestr("home-inspection.json", json.dumps(result, indent=2))
    print(f"Saved {bundle}. Review identifiers and upload this ZIP.")
    return 1 if result.get("collection_failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
