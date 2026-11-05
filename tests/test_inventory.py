import unittest
import subprocess
from unittest.mock import patch
import inventory


class InventoryTests(unittest.TestCase):
    def test_legacy_install_progress_on_stderr_is_not_failure(self):
        result = subprocess.CompletedProcess([], 0, "Success\n",
            r"C:\Downloads\firecube-home-bridge.apk: 1 file pushed, 0 skipped. 1.1 MB/s (840677 bytes in 0.704s)")
        with patch("inventory.subprocess.run", return_value=result):
            self.assertIn("Success", inventory.run("adb", "stick", "install", "-r", "bridge.apk").splitlines())

    def test_install_success_on_stderr_is_retained(self):
        result = subprocess.CompletedProcess([], 0, "", "1 file pushed\nSuccess\n")
        with patch("inventory.subprocess.run", return_value=result):
            self.assertIn("Success", inventory.run("adb", "stick", "install", "bridge.apk").splitlines())

    def test_install_failure_retains_both_streams(self):
        result = subprocess.CompletedProcess([], 1, "Failure [INSTALL_FAILED_INVALID_APK]", "1 file pushed")
        with patch("inventory.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "INSTALL_FAILED_INVALID_APK") as error:
                inventory.run("adb", "stick", "install", "bridge.apk")
        self.assertIn("1 file pushed", str(error.exception))

    def test_zero_exit_security_errors_on_either_stream_still_fail(self):
        for stdout, stderr in (("", "java.lang.SecurityException: Permission Denial"),
                               ("Error: Permission Denial", ""),
                               ("Failure [INSTALL_FAILED_USER_RESTRICTED]", "")):
            with self.subTest(stdout=stdout, stderr=stderr):
                result = subprocess.CompletedProcess([], 0, stdout, stderr)
                with patch("inventory.subprocess.run", return_value=result):
                    with self.assertRaises(RuntimeError):
                        inventory.run("adb", "stick", "shell", "pm", "disable-user", "probe")

    def test_read_output_is_not_polluted_by_daemon_startup_messages(self):
        result = subprocess.CompletedProcess([], 0, "package:android\n", "* daemon started successfully\n")
        with patch("inventory.subprocess.run", return_value=result):
            self.assertEqual(inventory.run("adb", "stick", "shell", "pm", "list", "packages"), "package:android")

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
