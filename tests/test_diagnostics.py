import unittest
from unittest.mock import patch
from diagnostics import capture


class DiagnosticTests(unittest.TestCase):
    def test_unsupported_command_is_recorded_and_other_reads_continue(self):
        baseline = {"packages": [{"package": "com.amazon.tv.launcher", "system": True, "enabled": True}]}
        calls = []

        def fake(adb, serial, *args):
            calls.append(args)
            if args[1:3] == ("pm", "resolve-activity"):
                raise RuntimeError("unknown command")
            return "read-only result"

        with patch("diagnostics.collect", return_value=baseline), patch("diagnostics.run", side_effect=fake):
            report = capture("adb", "stick")
        self.assertFalse(report["evidence"]["home_resolution"]["ok"])
        self.assertTrue(report["evidence"]["com.amazon.tv.launcher"]["ok"])
        self.assertFalse(report["home_compatibility"]["stock_launcher_disable_allowed"])
        self.assertTrue(all(args[0] == "shell" for args in calls))
        self.assertFalse(any("disable-user" in args or "enable" in args for args in calls))
