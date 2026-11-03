import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from recovery_probe import test_probe, PACKAGE


class ProbeTests(unittest.TestCase):
    def execute(self, verify_failure=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "audit.jsonl"
        mutations = []
        override = 0

        def fake(adb, serial, *args):
            nonlocal override
            if args[1:3] == ("getprop", "ro.build.fingerprint"):
                return "same-device"
            if args[1] == "dumpsys":
                return f"  User 0: installed=true hidden=false enabled={override}"
            self.assertEqual(args[1], "pm")
            self.assertEqual(args[-1], PACKAGE)
            # Audit intent must already be durable when a mutation starts.
            self.assertEqual(json.loads(path.read_text().splitlines()[-1])["event"], "command_intent")
            mutations.append(args[2])
            if not verify_failure:
                override = 3 if args[2] == "disable-user" else 1
            return "Success"

        with patch("recovery_probe.run", side_effect=fake):
            if verify_failure:
                with self.assertRaises(RuntimeError):
                    test_probe("adb", "stick", path)
            else:
                test_probe("adb", "stick", path)
        return path, mutations

    def test_audit_precedes_mutation_and_scope_is_probe_only(self):
        path, mutations = self.execute()
        self.assertEqual(mutations, ["disable-user", "enable"])
        result = json.loads(path.read_text().splitlines()[-1])
        self.assertTrue(result["probe_disable_enable_verified"])
        self.assertFalse(result["original_override_restored"])
        self.assertFalse(result["stock_launcher_recovery_verified"])

    def test_verification_failure_stops_before_next_change(self):
        path, mutations = self.execute(verify_failure=True)
        self.assertEqual(mutations, ["disable-user"])
        self.assertEqual(json.loads(path.read_text().splitlines()[-1])["event"], "stopped")

    def test_existing_journal_blocks_all_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            path.write_text("previous record")
            with patch("recovery_probe.run") as run:
                with self.assertRaises(FileExistsError):
                    test_probe("adb", "stick", path)
                run.assert_not_called()

    def test_permission_denial_checks_state_without_attempting_enable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            mutations = []
            def fake(adb, serial, *args):
                if args[1] == "getprop":
                    return "same-device"
                if args[1] == "dumpsys":
                    return "User 0: installed=true enabled=0"
                mutations.append(args[2])
                raise RuntimeError("java.lang.SecurityException: Permission Denial")
            with patch("recovery_probe.run", side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, "matching its original state"):
                    test_probe("adb", "stick", path)
            self.assertEqual(mutations, ["disable-user"])
            stopped = json.loads(path.read_text().splitlines()[-1])
            self.assertTrue(stopped["permission_denied"])
            self.assertTrue(stopped["original_override_unchanged"])
            self.assertIsNone(stopped["recovery_preview"])

    def test_failed_reenable_reports_verified_disabled_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            override = 0
            def fake(adb, serial, *args):
                nonlocal override
                if args[1] == "getprop":
                    return "same-device"
                if args[1] == "dumpsys":
                    return f"User 0: installed=true enabled={override}"
                if args[2] == "disable-user":
                    override = 3
                    return "Success"
                raise RuntimeError("permission denied")
            with patch("recovery_probe.run", side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, "verified disabled"):
                    test_probe("adb", "stick", path)
            stopped = json.loads(path.read_text().splitlines()[-1])
            self.assertEqual(stopped["final_override"], 3)
            self.assertEqual(stopped["recovery_preview"][-1], PACKAGE)
