"""A single checklist and export action; no device mutation controls."""
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QTextEdit, QFormLayout,
    QPushButton, QFileDialog, QLineEdit, QScrollArea, QMessageBox,
)
from acceptance import CHECKS, STATUSES, export_bundle


class AcceptanceWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, adb, serial, path, responses, notes, home, audit, parent=None):
        super().__init__(parent)
        self.arguments = (adb, serial, path, responses, notes, home, audit)

    def run(self):
        try:
            self.completed.emit(export_bundle(*self.arguments))
        except Exception as error:
            self.failed.emit(str(error))


class AcceptancePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        heading = QLabel("One acceptance round")
        heading.setStyleSheet("font-size: 24px; font-weight: bold")
        layout.addWidget(heading)
        notice = QLabel("Test the items you can, then export one bundle. Leave unrun checks as Not tested.\n"
                        "The export reads diagnostics and captures the current TV screen; it changes no apps or settings.\n"
                        "Reports include device identifiers, package metadata and the visible screen. Review before sharing.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        fields = QWidget()
        form = QFormLayout(fields)
        self.responses = {}
        for key, label in CHECKS.items():
            control = QComboBox()
            control.addItems(STATUSES)
            self.responses[key] = control
            form.addRow(label, control)
        self.home = QComboBox()
        self.home.addItems(["Not tested", "Amazon home", "Firecube", "Other/error"])
        form.addRow("What does the physical Home button open?", self.home)
        self.audit = QLineEdit()
        self.audit.setReadOnly(True)
        form.addRow("Optional disposable-probe audit", self.audit)
        browse = QPushButton("Attach probe audit…")
        browse.clicked.connect(self.choose_audit)
        form.addRow(browse)
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("What looked wrong or failed? Maximum 4000 characters.")
        self.notes.setMaximumHeight(110)
        form.addRow("Notes", self.notes)
        scroll.setWidget(fields)
        layout.addWidget(scroll)
        self.export = QPushButton("Export one acceptance bundle…")
        self.export.clicked.connect(self.export_results)
        layout.addWidget(self.export)
        self.result = QLabel("Not a 1.0 readiness certificate: package cleanup and home replacement remain unverified.")
        self.result.setWordWrap(True)
        layout.addWidget(self.result)

    def choose_audit(self):
        path, _ = QFileDialog.getOpenFileName(self, "Attach probe audit", "", "Probe audit (*.jsonl)")
        if path:
            self.audit.setText(path)

    def export_results(self):
        window = self.window
        if window.worker and window.worker.isRunning():
            QMessageBox.information(self, "Task running", "Wait for the current collection or probe test to finish.")
            return
        adb, serial = window.adb_path.text().strip(), window.serial.text().strip()
        if not serial or not Path(adb).is_file():
            QMessageBox.warning(self, "Connection details", "In Inventory, locate official ADB and enter the connected device identifier.")
            return
        if len(self.notes.toPlainText()) > 4000:
            QMessageBox.warning(self, "Notes too long", "Keep notes under 4000 characters.")
            return
        filename = "firecube-acceptance-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".zip"
        path, _ = QFileDialog.getSaveFileName(self, "Save acceptance bundle", filename, "Acceptance bundle (*.zip)")
        if not path:
            return
        if Path(path).exists():
            QMessageBox.warning(self, "File exists", "Choose a new filename to preserve existing results.")
            return
        self.export.setEnabled(False)
        window.refresh_button.setEnabled(False)
        window.diagnostic_button.setEnabled(False)
        window.probe_button.setEnabled(False)
        window.adb_path.setEnabled(False)
        window.serial.setEnabled(False)
        window.worker = AcceptanceWorker(adb, serial, path,
            {key: control.currentText() for key, control in self.responses.items()},
            self.notes.toPlainText(), self.home.currentText(), self.audit.text() or None, window)
        window.worker.completed.connect(lambda result: self.completed(result, path))
        window.worker.failed.connect(lambda error: self.failed(error, path))
        window.worker.finished.connect(window.collection_finished)
        window.worker.finished.connect(lambda: self.export.setEnabled(True))
        self.result.setText("Collecting read-only evidence. Leave the intended TV screen visible.")
        window.worker.start()

    def completed(self, result, path):
        counts = result["manual_counts"]
        self.result.setText(f"Saved {path}\nUser results: {counts}. No device changes applied.")

    def failed(self, error, path):
        self.result.setText("Collection failed. No device changes were applied; export may be incomplete.")
        QMessageBox.warning(self, "Acceptance export failed", f"{error}\nIf present, discard the incomplete export: {path}")
