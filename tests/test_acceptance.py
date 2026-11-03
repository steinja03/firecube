import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import zlib

from acceptance import CHECKS, export_bundle, validate_png


def tiny_png():
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\0\0\0\xff")) + chunk(b"IEND", b""))


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "results.zip"
        self.responses = {key: "Not tested" for key in CHECKS}
        self.diagnostic = {"baseline": {"properties": {"ro.build.fingerprint": "device-build"}}, "read_only": True}

    def test_unrun_checks_remain_unrun_and_bundle_contains_real_capture(self):
        with patch("acceptance.capture", return_value=self.diagnostic), patch("acceptance.screenshot", return_value=tiny_png()):
            report = export_bundle("adb", "stick", self.path, self.responses)
        self.assertEqual(report["manual_counts"]["Pass"], 0)
        self.assertEqual(report["manual_counts"]["Not tested"], len(CHECKS))
        self.assertFalse(report["requested_full_scope_ready"])
        with ZipFile(self.path) as bundle:
            self.assertEqual(bundle.read("current-screen.png"), tiny_png())
            self.assertEqual(json.loads(bundle.read("device-diagnostics.json")), self.diagnostic)

    def test_screenshot_failure_is_reported_without_fabricating_image(self):
        with patch("acceptance.capture", return_value=self.diagnostic), patch("acceptance.screenshot", side_effect=RuntimeError("unsupported")):
            report = export_bundle("adb", "stick", self.path, self.responses)
        self.assertFalse(report["screenshot"]["captured"])
        with ZipFile(self.path) as bundle:
            self.assertNotIn("current-screen.png", bundle.namelist())

    def test_existing_bundle_blocks_all_adb_reads(self):
        self.path.write_bytes(b"original")
        with patch("acceptance.capture") as capture:
            with self.assertRaises(FileExistsError):
                export_bundle("adb", "stick", self.path, self.responses)
            capture.assert_not_called()
        self.assertEqual(self.path.read_bytes(), b"original")

    def test_mismatched_probe_log_never_proves_this_device(self):
        audit = Path(self.directory.name) / "audit.jsonl"
        records = [{"event": "start", "device": "other-stick", "package": "dev.firecube.probe"},
                   {"event": "baseline", "fingerprint": "another-build"},
                   {"event": "complete", "probe_disable_enable_verified": True}]
        audit.write_text("\n".join(json.dumps(record) for record in records))
        with patch("acceptance.capture", return_value=self.diagnostic), patch("acceptance.screenshot", return_value=tiny_png()):
            report = export_bundle("adb", "stick", self.path, self.responses, probe_path=audit)
        self.assertFalse(report["probe_audit"]["matching_endpoint_and_fingerprint"])
        self.assertFalse(report["requested_full_scope_ready"])

    def test_png_corruption_is_rejected(self):
        validate_png(tiny_png())
        corrupt = bytearray(tiny_png())
        corrupt[20] ^= 1
        for data in (bytes(corrupt), tiny_png()[:-10], b"adb: error", tiny_png() + b"extra"):
            with self.assertRaises(ValueError):
                validate_png(data)
