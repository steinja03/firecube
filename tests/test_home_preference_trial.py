import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import home_preference_trial as trial


class HomePreferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.audit = Path(self.directory.name) / "trial.jsonl"
        self.before = {"preferred": None, "resolved": "com.amazon.tv.launcher/.ui.HomeActivity_vNext",
                       "home_preferences": [], "own_preference_count": 0, "own_exact_home_count": 0,
                       "permission": 0, "target_enabled": True}
        self.current = self.before.copy()
        self.calls = []
        self.home_succeeds = True
        self.apply_denied = False
        self.native_rollback = False
        self.restore_denied = False

    def native(self, adb, serial, mode, backup=None):
        self.calls.append(mode)
        if mode == "inspect":
            return {"ok": True, "state": self.current.copy()}
        if mode == "apply":
            self.assertEqual(json.loads(self.audit.read_text().splitlines()[-1])["event"], "preferred_home_intent")
            if self.apply_denied:
                return {"ok": False, "backup_written": True, "mutation_attempted": True, "error": "Permission Denial"}
            if self.native_rollback:
                return {"ok": False, "rollback_attempted": True, "rollback": {"restored": True}}
            self.current = {**self.before, "preferred": trial.TARGET, "resolved": trial.TARGET,
                            "own_preference_count": 1, "own_exact_home_count": 1,
                            "home_preferences": [{"component": trial.TARGET}]}
            return {"ok": True, "backup_written": True, "mutation_attempted": True, "preference_observed": True}
        if mode == "restore":
            if self.restore_denied:
                return {"ok": False, "error": "Restore blocked"}
            self.current = self.before.copy()
            return {"ok": True, "rollback": {"restored": True}}
        raise AssertionError(mode)

    def execute(self, on_apply_ready=None):
        def adb(adb, serial, *args):
            if args == ("shell", "input", "keyevent", "3"):
                return ""
            self.assertEqual(args, ("shell", "dumpsys", "activity", "activities"))
            package = "dev.firecube.launcher" if self.home_succeeds else "com.amazon.tv.launcher"
            return f"mResumedActivity: ActivityRecord{{uid {package}/.MainActivity}}"
        with patch("home_preference_trial.identity", return_value={"device": "same"}), \
             patch("home_preference_trial.accessibility", return_value={"enabled": "0"}), \
             patch("home_preference_trial.prepare"), patch("home_preference_trial.native", side_effect=self.native), \
             patch("home_preference_trial.run", side_effect=adb), patch("home_preference_trial.time.sleep"):
            return trial.run_trial("adb", "stick", "payload.apk", self.audit, on_apply_ready=on_apply_ready)

    def events(self):
        return [json.loads(line) for line in self.audit.read_text().splitlines()]

    def test_success_requires_home_observation_and_keeps_trial_preference(self):
        remember = Mock()
        backup = self.execute(remember)
        remember.assert_called_once_with()
        self.assertRegex(backup, trial.BACKUP_PATTERN)
        self.assertEqual(self.current["resolved"], trial.TARGET)
        self.assertEqual(self.events()[-1]["event"], "complete")
        self.assertFalse(self.events()[-1]["stock_launcher_disabled"])
        self.assertNotIn("restore", self.calls)

    def test_granted_permission_does_not_turn_actual_denial_into_success(self):
        self.apply_denied = True
        with self.assertRaisesRegex(RuntimeError, "Permission Denial"):
            self.execute()
        self.assertEqual(self.events()[-1]["event"], "rollback_verified")
        self.assertEqual(self.current, self.before)

    def test_home_still_opening_amazon_triggers_scoped_restore(self):
        self.home_succeeds = False
        with self.assertRaisesRegex(RuntimeError, "injected Home"):
            self.execute()
        self.assertEqual(self.current, self.before)
        self.assertEqual(self.calls.count("restore"), 1)
        self.assertFalse(any(event["event"] == "complete" for event in self.events()))

    def test_original_preferences_are_not_overwritten(self):
        self.current = {**self.before, "preferred": "other/.Home", "home_preferences": [{"component": "other/.Home"}]}
        remember = Mock()
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            self.execute(remember)
        self.assertNotIn("apply", self.calls)
        remember.assert_not_called()

    def test_native_rollback_is_not_repeated_blindly(self):
        self.native_rollback = True
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertNotIn("restore", self.calls)
        self.assertTrue(any(event["event"] == "rollback_verified" for event in self.events()))

    def test_unverified_restore_stays_explicit(self):
        self.home_succeeds = False
        self.restore_denied = True
        with self.assertRaises(RuntimeError):
            self.execute()
        self.assertEqual(self.events()[-1]["event"], "rollback_unverified")

    def test_existing_audit_blocks_all_device_access(self):
        self.audit.write_text("original")
        with patch("home_preference_trial.identity") as identity:
            with self.assertRaises(FileExistsError):
                trial.run_trial("adb", "stick", "payload.apk", self.audit)
            identity.assert_not_called()
        self.assertEqual(self.audit.read_text(), "original")

    def test_wrong_device_blocks_restore(self):
        original = Path(self.directory.name) / "original.jsonl"
        original.write_text(json.dumps({"event": "baseline", "identity": {"device": "first"},
            "remote_backup": "/data/local/tmp/firecube-homepref-backup-0123456789abcdef.json"}) + "\n")
        with patch("home_preference_trial.identity", return_value={"device": "other"}), patch("home_preference_trial.prepare") as prepare:
            with self.assertRaisesRegex(RuntimeError, "Wrong device"):
                trial.restore_trial("adb", "stick", "payload.apk", original, self.audit)
            prepare.assert_not_called()

    def test_unknown_modes_and_untrusted_backup_paths_never_reach_adb(self):
        with patch("home_preference_trial.run") as run:
            with self.assertRaises(ValueError):
                trial.native("adb", "stick", "disable")
            with self.assertRaises(ValueError):
                trial.native("adb", "stick", "restore", "/data/local/tmp/backup; reboot")
            run.assert_not_called()
