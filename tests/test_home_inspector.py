import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import home_inspect_runner as inspector


class InspectorTests(unittest.TestCase):
    def test_queries_and_temp_copy_never_install_or_change_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = Path(folder) / "inspector.apk"
            payload.write_bytes(b"known inspector")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            calls = []
            def fake(adb, serial, *args):
                calls.append(args)
                if args[:2] == ("shell", "getprop"):
                    return "tank" if args[-1] == "ro.product.device" else "22"
                if args[:2] == ("shell", "settings"):
                    self.assertIn("get", args)
                    return "0" if args[-1] == "accessibility_enabled" else ""
                if args[0] == "push":
                    return "1 file pushed"
                if args[0] == "pull":
                    Path(args[-1]).write_bytes(payload.read_bytes())
                    return "1 file pulled"
                self.assertEqual(args[1], "CLASSPATH=" + inspector.REMOTE)
                return json.dumps({"read_only": True, "mode": "inspect", "uid": 2000})
            with patch("home_inspect_runner.PAYLOAD_SHA256", digest), patch("home_inspect_runner.run", side_effect=fake):
                result = inspector.inspect("adb", "stick", payload)
            self.assertTrue(result["accessibility_readbacks_unchanged"])
            self.assertFalse(any("install" in call or "put" in call or "delete" in call for call in calls))

    def test_bad_payload_hash_blocks_device_access(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = Path(folder) / "payload.apk"
            payload.write_bytes(b"wrong")
            with patch("home_inspect_runner.run") as run:
                with self.assertRaisesRegex(RuntimeError, "checksum"):
                    inspector.inspect("adb", "stick", payload)
                run.assert_not_called()

    def test_transferred_hash_mismatch_prevents_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = Path(folder) / "payload.apk"
            payload.write_bytes(b"known")
            calls = []
            def fake(adb, serial, *args):
                calls.append(args)
                if args[0] == "pull":
                    Path(args[-1]).write_bytes(b"corrupt")
                if args[:2] == ("shell", "getprop"):
                    return "tank" if args[-1] == "ro.product.device" else "22"
                return ""
            with patch("home_inspect_runner.PAYLOAD_SHA256", hashlib.sha256(payload.read_bytes()).hexdigest()), patch("home_inspect_runner.run", side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, "Transferred"):
                    inspector.inspect("adb", "stick", payload)
            self.assertFalse(any("app_process" in call for call in calls))
