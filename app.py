"""Fire TV inventory, diagnostics, and an opt-in disposable recovery test."""
import argparse
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QInputDialog,
)

from baseline import load_report
from inventory import collect
from safety import assess, details
from diagnostics import capture
from recovery_probe import test_probe


class RecoveryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, adb, serial, journal, parent=None):
        super().__init__(parent)
        self.adb, self.serial, self.journal = adb, serial, journal

    def run(self):
        try:
            test_probe(self.adb, self.serial, self.journal)
            last = Path(self.journal).read_text(encoding="utf-8").splitlines()[-1]
            result = json.loads(last)
            if result.get("event") != "complete" or result.get("probe_disable_enable_verified") is not True:
                raise RuntimeError("No verified probe completion record")
            self.completed.emit(result)
        except Exception as error:
            self.failed.emit(str(error))


class Collector(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, adb, serial, parent=None, diagnostics=False):
        super().__init__(parent)
        self.adb, self.serial = adb, serial
        self.diagnostics = diagnostics

    def run(self):
        try:
            self.completed.emit((capture if self.diagnostics else collect)(self.adb, self.serial))
        except Exception as error:
            self.failed.emit(str(error))


class InventoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.report = None
        self.visible = []
        self.worker = None
        self.diagnostic_path = None
        self.setWindowTitle("Firecube · Package inventory")
        self.resize(1080, 760)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        heading = QLabel("Fire TV package inventory")
        heading.setStyleSheet("font-size: 24px; font-weight: bold")
        layout.addWidget(heading)
        layout.addWidget(QLabel("Inventory and diagnostics · Recovery test changes only the disposable Firecube test app"))
        open_button = QPushButton("Open baseline JSON…")
        open_button.clicked.connect(self.choose_report)
        layout.addWidget(open_button)
        live = QHBoxLayout()
        self.adb_path = QLineEdit(shutil.which("adb") or str(Path("adb.exe").resolve()))
        self.adb_path.setPlaceholderText("Full path to adb.exe")
        self.serial = QLineEdit()
        self.serial.setPlaceholderText("Device identifier, for example 192.168.50.39:5555")
        browse_adb = QPushButton("Locate ADB…")
        browse_adb.clicked.connect(self.choose_adb)
        self.refresh_button = QPushButton("Read from Stick")
        self.refresh_button.clicked.connect(self.collect_live)
        self.save_button = QPushButton("Save baseline…")
        self.save_button.clicked.connect(self.save_report)
        self.save_button.setEnabled(False)
        self.diagnostic_button = QPushButton("Export device diagnostics…")
        self.diagnostic_button.clicked.connect(self.collect_diagnostics)
        for control in (self.adb_path, browse_adb, self.serial, self.refresh_button, self.save_button):
            live.addWidget(control)
        layout.addLayout(live)
        layout.addWidget(self.diagnostic_button)
        self.probe_button = QPushButton("Test disposable app disable/enable…")
        self.probe_button.clicked.connect(self.probe_recovery)
        layout.addWidget(self.probe_button)
        layout.addWidget(QLabel("Connect with adb connect first. Refresh reads only; it does not install or change packages."))
        self.summary = QLabel("Open a baseline to begin. Saved reports do not represent live device status.")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.summary)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search package identifier")
        self.kind = QComboBox()
        self.kind.addItems(["All types", "System", "Non-system"])
        self.state = QComboBox()
        self.state.addItems(["All states", "Enabled", "Disabled"])
        for control in (self.search, self.kind, self.state):
            filters.addWidget(control)
        self.search.textChanged.connect(self.refresh)
        self.kind.currentIndexChanged.connect(self.refresh)
        self.state.currentIndexChanged.connect(self.refresh)
        layout.addLayout(filters)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Package identifier", "Type", "Recorded state", "Disabling risk"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.show_details)
        layout.addWidget(self.table, 1)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(175)
        layout.addWidget(self.details)
        self.statusBar().showMessage("Package-state baseline only; app data and firmware are not backed up.")

    def choose_report(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open baseline", "", "JSON reports (*.json)")
        if path:
            self.open_report(path)

    def choose_adb(self):
        path, _ = QFileDialog.getOpenFileName(self, "Locate official platform-tools ADB", "", "ADB executable (adb.exe adb);;All files (*)")
        if path:
            self.adb_path.setText(path)

    def probe_recovery(self):
        if self.worker and self.worker.isRunning():
            return
        adb, serial = self.adb_path.text().strip(), self.serial.text().strip()
        if not serial or not Path(adb).is_file():
            QMessageBox.warning(self, "Connection details", "Locate adb.exe and enter the exact connected device identifier.")
            return
        answer, accepted = QInputDialog.getText(self, "Preview: disposable app test",
            f"Device: {serial}\n"
            "Requires dev.firecube.probe already installed.\n"
            "Changes only that test app, for user 0:\n"
            "1. pm disable-user --user 0 dev.firecube.probe\n"
            "2. Verify, then pm enable --user 0 dev.firecube.probe\n"
            "3. Verify enabled state. Stop on any failure.\n"
            "Final override is explicitly enabled; original default override may differ.\n"
            "Amazon home, Alexa and streaming apps are not changed.\n"
            "Type TEST PROBE to approve:")
        if not accepted or answer.strip() != "TEST PROBE":
            return
        filename = "probe-audit-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".jsonl"
        path, _ = QFileDialog.getSaveFileName(self, "Save durable test audit", filename, "Audit log (*.jsonl)")
        if not path:
            return
        if Path(path).exists():
            QMessageBox.warning(self, "File exists", "Choose a new audit file. Nothing changed.")
            return
        self.refresh_button.setEnabled(False)
        self.diagnostic_button.setEnabled(False)
        self.probe_button.setEnabled(False)
        self.adb_path.setEnabled(False)
        self.serial.setEnabled(False)
        self.worker = RecoveryWorker(adb, serial, path, self)
        self.worker.completed.connect(self.probe_completed)
        self.worker.failed.connect(lambda error: self.probe_failed(error, path, serial))
        self.worker.finished.connect(self.collection_finished)
        self.statusBar().showMessage("Testing only disposable probe. Do not disconnect the Stick.")
        self.worker.start()

    def probe_completed(self, result):
        self.details.setPlainText(json.dumps(result, indent=2))
        self.statusBar().showMessage("Probe disable/enable verified. Refresh inventory; system-package and launcher recovery remain unverified.")

    def probe_failed(self, error, path, serial):
        self.statusBar().showMessage("Probe test stopped. Inspect its audit before another operation.")
        QMessageBox.warning(self, "Probe test stopped",
            f"{error}\nAudit: {path}\n"
            "The probe may be disabled. Inspect the audit. Its recovery command is:\n"
            f"adb -s {serial} shell pm enable --user 0 dev.firecube.probe")

    def open_report(self, path):
        try:
            report = load_report(path)
        except (OSError, ValueError, RecursionError) as error:
            QMessageBox.warning(self, "Cannot open baseline", str(error))
            return False
        self.display_report(report)
        return True

    def display_report(self, report):
        self.report = report
        self.save_button.setEnabled(True)
        props = report["properties"]
        packages = report["packages"]
        system = sum(p["system"] for p in packages)
        disabled = sum(not p["enabled"] for p in packages)
        self.summary.setText(
            f"{props.get('ro.product.model', 'Unknown model')} · "
            f"{props.get('ro.build.version.name', 'Unknown firmware')} · "
            f"API {props.get('ro.build.version.sdk', '?')}\n"
            f"{len(packages)} packages · {system} system · {len(packages)-system} non-system · "
            f"{disabled} disabled\nSaved snapshot; connection and restoration are unverified."
        )
        self.refresh()

    def collect_diagnostics(self):
        if self.worker and self.worker.isRunning():
            return
        filename = "firecube-evidence-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, "Save read-only diagnostics", filename, "JSON reports (*.json)")
        if path:
            if Path(path).exists():
                QMessageBox.warning(self, "File exists", "Choose a new filename to preserve existing reports.")
                return
            self.collect_live(diagnostic_path=path)

    def collect_live(self, _checked=False, diagnostic_path=None):
        if self.worker and self.worker.isRunning():
            return
        serial = self.serial.text().strip()
        adb = self.adb_path.text().strip()
        if not serial or not Path(adb).is_file():
            QMessageBox.warning(self, "Connection details", "Enter the exact device identifier and a valid adb executable path.")
            return
        self.refresh_button.setEnabled(False)
        self.diagnostic_button.setEnabled(False)
        self.probe_button.setEnabled(False)
        self.adb_path.setEnabled(False)
        self.serial.setEnabled(False)
        self.diagnostic_path = diagnostic_path
        self.statusBar().showMessage("Reading device and package states… Previous report remains available.")
        self.worker = Collector(adb, serial, self, diagnostics=diagnostic_path is not None)
        self.worker.completed.connect(self.live_completed)
        self.worker.failed.connect(self.live_failed)
        self.worker.finished.connect(self.collection_finished)
        self.worker.start()

    def live_completed(self, report):
        if self.diagnostic_path:
            path = self.diagnostic_path
            self.diagnostic_path = None
            try:
                with open(path, "x", encoding="utf-8") as stream:
                    json.dump(report, stream, indent=2)
                    stream.write("\n")
            except (OSError, ValueError) as error:
                self.live_failed(str(error))
                return
            self.display_report(report["baseline"])
            compatibility = report["home_compatibility"]
            self.statusBar().showMessage("Diagnostics saved. Default Home, reboot and recovery remain unverified.")
            self.details.setPlainText(json.dumps(compatibility, indent=2))
            return
        self.display_report(report)
        self.statusBar().showMessage("Read completed. Save a baseline to retain it; current connection is not monitored.")

    def live_failed(self, error):
        self.diagnostic_path = None
        self.statusBar().showMessage("Read failed. Previous report retained.")
        QMessageBox.warning(self, "Read stopped", error)

    def collection_finished(self):
        self.refresh_button.setEnabled(True)
        self.diagnostic_button.setEnabled(True)
        self.probe_button.setEnabled(True)
        self.adb_path.setEnabled(True)
        self.serial.setEnabled(True)

    def save_report(self):
        if self.report is None:
            return
        filename = "stick-baseline-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, "Save baseline", filename, "JSON reports (*.json)")
        if not path:
            return
        try:
            with open(path, "x", encoding="utf-8") as stream:
                json.dump(self.report, stream, indent=2)
                stream.write("\n")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Save stopped", str(error))
            return
        self.statusBar().showMessage("Baseline saved. This contains package states, not app data or firmware.")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Read in progress", "Wait for the current read to finish before closing.")
            event.ignore()
        else:
            event.accept()

    def refresh(self, *_):
        self.visible = []
        if self.report:
            for package in sorted(self.report["packages"], key=lambda p: p["package"]):
                if self.search.text().strip().lower() not in package["package"].lower():
                    continue
                if self.kind.currentIndex() and package["system"] != (self.kind.currentIndex() == 1):
                    continue
                if self.state.currentIndex() and package["enabled"] != (self.state.currentIndex() == 1):
                    continue
                self.visible.append(package)
        self.table.setRowCount(len(self.visible))
        for row, package in enumerate(self.visible):
            values = [package["package"], "System" if package["system"] else "Non-system",
                      "Enabled" if package["enabled"] else "Disabled",
                      "Protected by policy" if assess(package)["protected"] else "Unverified"]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.details.setPlainText(f"{len(self.visible)} matching packages. Select a row for details.")

    def show_details(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.visible):
            package = self.visible[row]
            self.details.setPlainText(details(package))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", nargs="?")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    window = InventoryWindow()
    window.show()
    if args.baseline:
        window.open_report(args.baseline)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
