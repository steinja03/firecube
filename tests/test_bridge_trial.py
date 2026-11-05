import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bridge_trial import apply_trial, planned_settings, restore_settings, service_ids, COMPONENT, SERVICES, ENABLED


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.apk = Path(self.directory.name) / "bridge.apk"
        self.apk.write_bytes(b"test apk")
        self.receipt = Path(self.directory.name) / "receipt.jsonl"
        self.values = {SERVICES: "reader.app/.Service$Inner", ENABLED: "1"}
        self.calls = []
        self.fail_key = None
        self.home_succeeds = True

    def run_fake(self, adb, serial, *args):
        self.calls.append(args)
        if args[0] == "install":
            return "Success"
        if args[1] == "getprop":
            return {"ro.product.device": "tank", "ro.serialno": "hardware-serial", "ro.build.fingerprint": "build"}[args[2]]
        if args[1:4] == ("pm", "list", "users"):
            return "Users:\n UserInfo{0:Owner:13} running\n UserInfo{10:Other:2}"
        if args[1:4] == ("pm", "list", "packages"):
            return "package:dev.firecube.launcher"
        if args[1] == "settings":
            action, key = args[4], args[6]
            if action == "get":
                return self.values[key]
            # Intent is persisted before any write.
            self.assertEqual(json.loads(self.receipt.read_text().splitlines()[-1])["event"], "setting_intent")
            if self.fail_key == key:
                raise RuntimeError("Permission Denial")
            self.values[key] = "null" if action == "delete" else shlex.split(args[7])[0]
            return ""
        if args[1:3] == ("am", "broadcast"):
            self.assertEqual(args[3:5], ("--user", "0"))
            return "Broadcast completed: result=1"
        if args[1] == "input":
            return ""
        if args[1] == "dumpsys":
            package = "dev.firecube.launcher" if self.home_succeeds else "com.amazon.tv.launcher"
            return f"mResumedActivity: ActivityRecord{{abc {package}/.MainActivity}}"
        raise AssertionError(args)

    def execute(self):
        digest = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        with patch("bridge_trial.APK_SHA256", digest), patch("bridge_trial.run", side_effect=self.run_fake), patch("bridge_trial.time.sleep"):
            apply_trial("adb", "stick", self.apk, self.receipt)

    def test_addition_preserves_other_services_and_verifies_home(self):
        self.execute()
        self.assertEqual(self.values[SERVICES], "reader.app/.Service$Inner:" + COMPONENT)
        events = [json.loads(line) for line in self.receipt.read_text().splitlines()]
        self.assertTrue(events[-1]["home_redirect_observed"])
        self.assertFalse(events[-1]["stock_launcher_disabled"])
        self.assertFalse(any("disable-user" in call or "uninstall" in call for call in self.calls))

    def test_permission_denial_does_not_replace_existing_services(self):
        self.fail_key = SERVICES
        before = self.values.copy()
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(self.values, before)
        self.assertEqual(json.loads(self.receipt.read_text().splitlines()[-1])["event"], "rollback_complete")

    def test_partial_failure_restores_exact_original_values(self):
        self.values[SERVICES] = "null"
        self.values[ENABLED] = "0"
        before = self.values.copy()
        self.fail_key = ENABLED
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(self.values, before)

    def test_failed_home_observation_rolls_back_instead_of_claiming_success(self):
        self.home_succeeds = False
        before = self.values.copy()
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(self.values, before)
        events = [json.loads(line) for line in self.receipt.read_text().splitlines()]
        self.assertFalse(any(event["event"] == "complete" for event in events))

    def test_bad_apk_checksum_blocks_all_adb_calls(self):
        with patch("bridge_trial.run") as run:
            with self.assertRaises(RuntimeError):
                apply_trial("adb", "stick", self.apk, self.receipt)
            run.assert_not_called()

    def test_concurrent_settings_changes_are_not_overwritten(self):
        before = {"device_identity": "serial", "fingerprint": "build", "settings": {SERVICES: "null", ENABLED: "0"}}
        current = {**before, "settings": {SERVICES: "other.app/.Service", ENABLED: "1"}}
        with patch("bridge_trial.snapshot", return_value=current), patch("bridge_trial.write_setting") as write:
            with self.assertRaisesRegex(RuntimeError, "outside this trial"):
                restore_settings("adb", "stick", before, planned_settings(before), lambda *args, **kwargs: None)
            write.assert_not_called()

    def test_invalid_service_value_is_rejected(self):
        with self.assertRaises(RuntimeError):
            service_ids("app/.Service; reboot")

    def test_inactive_existing_services_are_not_activated(self):
        before = {"settings": {SERVICES: "other.app/.Service", ENABLED: "0"}}
        with self.assertRaisesRegex(RuntimeError, "could activate"):
            planned_settings(before)

    def test_wrong_device_blocks_restoration_before_any_write(self):
        before = {"device_identity": "first", "fingerprint": "build", "settings": {SERVICES: "null", ENABLED: "0"}}
        current = {**before, "device_identity": "second"}
        with patch("bridge_trial.snapshot", return_value=current), patch("bridge_trial.write_setting") as write:
            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                restore_settings("adb", "stick", before, planned_settings(before), lambda *args, **kwargs: None)
            write.assert_not_called()

    def test_existing_receipt_is_not_overwritten(self):
        self.receipt.write_text("original audit")
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.receipt.read_text(), "original audit")

    def test_full_trial_accepts_legacy_install_progress_via_actual_adb_wrapper(self):
        def process(argv, **kwargs):
            output = self.run_fake(argv[0], argv[2], *argv[3:])
            progress = "C:\\Downloads\\bridge.apk: 1 file pushed, 0 skipped. 1.1 MB/s (840677 bytes in 0.704s)" if argv[3] == "install" else ""
            return subprocess.CompletedProcess(argv, 0, output, progress)
        digest = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        with patch("bridge_trial.APK_SHA256", digest), patch("inventory.subprocess.run", side_effect=process), patch("bridge_trial.time.sleep"):
            apply_trial("adb", "stick", self.apk, self.receipt)
        self.assertEqual(json.loads(self.receipt.read_text().splitlines()[-1])["event"], "complete")
