import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from app import InventoryWindow
from app import Collector
from baseline import load_report


class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "baseline.json"
        self.report = {"schema_version": 1, "properties": {"ro.product.model": "AFTT"},
                       "packages": [
                           {"package": "android", "system": True, "enabled": True},
                           {"package": "org.example.app", "system": False, "enabled": False}]}
        self.path.write_text(json.dumps(self.report))

    def test_import_and_combined_filters(self):
        window = InventoryWindow()
        self.addCleanup(window.close)
        self.assertTrue(window.open_report(self.path))
        self.assertEqual(window.table.rowCount(), 2)
        window.kind.setCurrentIndex(2)
        window.state.setCurrentIndex(2)
        self.assertEqual(window.table.rowCount(), 1)
        window.table.selectRow(0)
        self.assertIn("Restoration: unverified", window.details.toPlainText())
        window.search.setText("missing")
        self.assertEqual(window.table.rowCount(), 0)

    def test_duplicate_and_nonboolean_states_rejected(self):
        self.report["packages"].append(self.report["packages"][0])
        self.path.write_text(json.dumps(self.report))
        with self.assertRaises(ValueError):
            load_report(self.path)

    def test_collector_success_and_error_signals(self):
        worker = Collector("adb", "test")
        reports, errors = [], []
        worker.completed.connect(reports.append)
        worker.failed.connect(errors.append)
        with patch("app.collect", return_value=self.report):
            worker.run()
        self.assertEqual(reports, [self.report])
        with patch("app.collect", side_effect=RuntimeError("offline")):
            worker.run()
        self.assertEqual(errors, ["offline"])

    def test_save_refuses_existing_file(self):
        window = InventoryWindow()
        self.addCleanup(window.close)
        window.display_report(self.report)
        original = self.path.read_bytes()
        with patch("app.QFileDialog.getSaveFileName", return_value=(str(self.path), "")):
            with patch("app.QMessageBox.warning") as warning:
                window.save_report()
                warning.assert_called_once()
        self.assertEqual(self.path.read_bytes(), original)
        self.report["packages"].pop()
        self.report["packages"][0]["enabled"] = "false"
        self.path.write_text(json.dumps(self.report))
        with self.assertRaises(ValueError):
            load_report(self.path)
