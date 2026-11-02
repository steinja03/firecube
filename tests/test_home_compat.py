import unittest
from home_compat import summarize


class HomeCompatibilityTests(unittest.TestCase):
    def test_help_and_resolution_never_authorize_stock_launcher_disable(self):
        result = summarize({
            "package_manager_help": {"ok": True, "output": "pm set-home-activity COMPONENT\n  disable-user [--user ID]\n  default-state PACKAGE"},
            "home_resolution": {"ok": True, "output": "dev.firecube.launcher/.MainActivity"},
        })
        self.assertTrue(result["pm_set_home_advertised"])
        self.assertTrue(result["pm_disable_user_advertised"])
        self.assertEqual(result["resolved_home_component"], "dev.firecube.launcher/.MainActivity")
        self.assertFalse(result["stock_launcher_disable_allowed"])
        self.assertFalse(result["home_button_verified"])

    def test_error_and_ambiguous_outputs_are_not_readiness(self):
        for output in ("Error: unknown command", "", "a.b/.A\nc.d/.B"):
            result = summarize({"home_resolution": {"ok": True, "output": output}})
            self.assertIsNone(result["resolved_home_component"])
            self.assertFalse(result["pm_set_home_advertised"])
