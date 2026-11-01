import unittest
from safety import assess


class SafetyTests(unittest.TestCase):
    def test_exact_guards_and_unknowns(self):
        for name in ("android", "com.android.bluetooth", "com.amazon.tv.launcher"):
            self.assertTrue(assess({"package": name, "system": True})["protected"])
        for name in ("com.amazon.tv.launcher.fake", "com.example.app"):
            result = assess({"package": name, "system": False})
            self.assertFalse(result["protected"])
            self.assertIn("Unverified", result["risk"])

    def test_system_flag_does_not_establish_safety(self):
        result = assess({"package": "com.example.app", "system": True})
        self.assertEqual(result["category"], "Unreviewed system package")
        self.assertIn("Unverified", result["risk"])
