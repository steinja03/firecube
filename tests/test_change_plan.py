import unittest
from change_plan import preview, KEEP


class PlanTests(unittest.TestCase):
    def test_streaming_apps_and_launcher_always_kept(self):
        report = {"packages": [{"package": p, "system": False, "enabled": True} for p in KEEP]}
        for row in preview(report):
            self.assertEqual(row["status"], "keep")
            self.assertFalse(row["apply_allowed"])
            self.assertEqual(row["commands"], [])

    def test_alexa_is_review_candidate_not_disable_recommendation(self):
        rows = preview({"packages": [
            {"package": "com.amazon.vizzini", "system": True, "enabled": True},
            {"package": "com.android.bluetooth", "system": True, "enabled": True},
            {"package": "org.example.app", "system": False, "enabled": True},
        ]})
        self.assertIn("unverified", rows[0]["status"])
        self.assertEqual(rows[1]["status"], "protected")
        self.assertTrue(all(not r["apply_allowed"] for r in rows))
