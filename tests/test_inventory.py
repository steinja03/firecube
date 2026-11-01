import unittest
from unittest.mock import patch
import inventory


class InventoryTests(unittest.TestCase):
    def test_package_parser_rejects_shell_errors(self):
        with self.assertRaises(ValueError):
            inventory.package_names("Error: permission denied")

    def test_package_parser(self):
        self.assertEqual(inventory.package_names("package:android\npackage:com.amazon.tv.launcher\n"),
                         {"android", "com.amazon.tv.launcher"})

    def response(self, adb, serial, *args):
        self.assertEqual(serial, "test-stick")
        if args == ("get-state",):
            return "device"
        self.assertEqual(args[0], "shell")
        if args[1] == "getprop":
            return "test-build"
        if args[1] == "id":
            return "uid=2000(shell)"
        self.assertEqual(args[1:4], ("pm", "list", "packages"))
        return "" if args[-1] == "-d" else "package:android"

    def test_read_only_inventory(self):
        with patch.object(inventory, "run", side_effect=self.response):
            report = inventory.collect("adb", "test-stick")
        self.assertTrue(report["packages"][0]["enabled"])
        self.assertIsNone(report["packages"][0]["restorable"])
        self.assertFalse(report["restoration_verified"])

    def test_inconsistent_states_stop_collection(self):
        def response(adb, serial, *args):
            return "package:android" if args[-1] == "-d" else self.response(adb, serial, *args)
        with patch.object(inventory, "run", side_effect=response):
            with self.assertRaises(RuntimeError):
                inventory.collect("adb", "test-stick")


if __name__ == "__main__":
    unittest.main()
