"""One read-only evidence bundle plus explicitly user-reported acceptance results."""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
import zlib
from zipfile import ZipFile, ZIP_DEFLATED

from diagnostics import capture

CHECKS = {
    "netflix": "Netflix: launch, play, pause and return",
    "youtube": "YouTube: launch, play and return",
    "paramount": "Paramount+: launch, play and return",
    "hulu": "Hulu: launch, play and return",
    "max": "Max/HBO Max: launch, play and return",
    "disney": "Disney+: launch, play and return",
    "plex": "Plex: launch, play and return",
    "peacock": "Peacock: launch, play and return",
    "remote": "D-pad, Select, Back and long-press app menu",
    "favorites": "Favorite order and hiding persist after reopening",
    "design": "Artwork, text and focus are readable from the couch",
    "preferences": "Theme and heading persist after reopening",
    "reboot": "After a normal reboot, manually open Firecube; preferences persist",
    "settings_transfer": "Export/import settings (file picker may be unavailable)",
}
STATUSES = ("Not tested", "Pass", "Fail", "Unavailable")


def validate_png(data):
    if len(data) > 16 * 1024 * 1024 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Screenshot is not a supported PNG")
    offset = 8
    first = True
    has_image_data = False
    while offset + 12 <= len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError("Truncated screenshot")
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", data[offset + 8 + size:end])[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            raise ValueError("Screenshot checksum failed")
        if first:
            if kind != b"IHDR" or size != 13:
                raise ValueError("Invalid screenshot header")
            width, height = struct.unpack(">II", body[:8])
            if not (1 <= width <= 7680 and 1 <= height <= 4320):
                raise ValueError("Unexpected screenshot dimensions")
            first = False
        if kind == b"IDAT" and size:
            has_image_data = True
        if kind == b"IEND":
            if size != 0 or end != len(data) or not has_image_data:
                raise ValueError("Invalid screenshot end")
            return
        offset = end
    raise ValueError("Screenshot has no end marker")


def screenshot(adb, serial):
    result = subprocess.run([adb, "-s", serial, "exec-out", "screencap", "-p"],
                            capture_output=True, timeout=45)
    if result.returncode or result.stderr.strip():
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace") or "Screenshot command failed")
    validate_png(result.stdout)
    return result.stdout


def export_bundle(adb, serial, path, responses, notes="", home_result="Not tested", probe_path=None):
    if set(responses) != set(CHECKS) or any(value not in STATUSES for value in responses.values()):
        raise ValueError("Invalid acceptance responses")
    if home_result not in ("Not tested", "Amazon home", "Firecube", "Other/error"):
        raise ValueError("Invalid Home result")
    if not isinstance(notes, str) or len(notes) > 4000:
        raise ValueError("Notes exceed 4000 characters")
    # Exclusive file creation happens before any potentially slow ADB collection.
    with Path(path).open("xb") as stream:
        diagnostic = capture(adb, serial)
        screen = None
        try:
            screen = screenshot(adb, serial)
            screen_result = {"captured": True, "description": "Current device screen; may be Amazon home or an app"}
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            screen_result = {"captured": False, "error": str(error)}
        audit = None
        audit_info = {"attached": False}
        if probe_path:
            p = Path(probe_path)
            if p.stat().st_size > 1024 * 1024:
                raise ValueError("Probe audit exceeds 1 MB")
            audit = p.read_text(encoding="utf-8-sig")
            records = [json.loads(line) for line in audit.splitlines() if line.strip()]
            if not records or any(not isinstance(record, dict) for record in records):
                raise ValueError("Invalid probe audit")
            start, last = records[0], records[-1]
            matching = start.get("device") == serial and start.get("package") == "dev.firecube.probe"
            fingerprints = [record.get("fingerprint") for record in records if record.get("event") == "baseline"]
            matching = matching and fingerprints == [diagnostic["baseline"]["properties"].get("ro.build.fingerprint")]
            audit_info = {"attached": True, "matching_endpoint_and_fingerprint": matching,
                          "reports_completion": last.get("event") == "complete" and last.get("probe_disable_enable_verified") is True,
                          "source": "Imported user-selected audit; authenticity and current device state are not independently verified"}
        report = {
            "schema_version": 1, "candidate": "0.5.0",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "manual_results": responses, "manual_results_source": "User observations, not automated tests",
            "manual_counts": {status: list(responses.values()).count(status) for status in STATUSES},
            "home_button_observation": home_result, "notes": notes,
            "screenshot": screen_result, "probe_audit": audit_info,
            "requested_full_scope_ready": False,
            "remaining_scope": ["Alexa cleanup unverified", "Existing-app disable/restore unverified",
                                "Replacement Home-button behavior and stock-launcher recovery unverified"],
            "device_mutations_performed_by_export": False,
        }
        with ZipFile(stream, "w", ZIP_DEFLATED) as bundle:
            bundle.writestr("acceptance.json", json.dumps(report, indent=2))
            bundle.writestr("device-diagnostics.json", json.dumps(diagnostic, indent=2))
            if screen is not None:
                bundle.writestr("current-screen.png", screen)
            if audit is not None:
                bundle.writestr("probe-audit.jsonl", audit)
        return report
