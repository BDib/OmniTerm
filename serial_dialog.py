"""
Serial connection dialog for OmniTerm.

Modal dialog for entering serial port connection details: port, baud rate,
data bits, parity, stop bits.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QLabel, QPushButton, QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt


class SerialDialog(QDialog):
    """Modal dialog that collects serial connection parameters."""

    BAUD_RATES = [
        300, 1200, 2400, 4800, 9600, 19200, 38400,
        57600, 115200, 230400, 460800, 921600,
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Connection")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)

        # ── Form ──
        form = QFormLayout()

        # Port selector with refresh
        port_layout = QHBoxLayout()
        self._port = QComboBox()
        self._port.setEditable(True)
        self._port.setPlaceholderText("e.g., COM3 or /dev/ttyUSB0")
        self._refresh_ports()
        port_layout.addWidget(self._port)
        refresh_btn = QPushButton("\u21BB")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addWidget(refresh_btn)
        form.addRow("Port:", port_layout)

        self._baud = QComboBox()
        for rate in self.BAUD_RATES:
            self._baud.addItem(str(rate), rate)
        self._baud.setCurrentText("115200")
        form.addRow("Baud Rate:", self._baud)

        self._databits = QSpinBox()
        self._databits.setRange(5, 8)
        self._databits.setValue(8)
        form.addRow("Data Bits:", self._databits)

        self._parity = QComboBox()
        self._parity.addItems(["None", "Even", "Odd", "Mark", "Space"])
        form.addRow("Parity:", self._parity)

        self._stopbits = QComboBox()
        self._stopbits.addItems(["1", "1.5", "2"])
        form.addRow("Stop Bits:", self._stopbits)

        self._flow_control = QCheckBox("Hardware Flow Control (RTS/CTS)")
        self._flow_control.setChecked(False)
        form.addRow("", self._flow_control)

        layout.addLayout(form)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        connect_btn = QPushButton("Connect")
        connect_btn.setDefault(True)
        connect_btn.clicked.connect(self._on_connect)
        btn_layout.addWidget(connect_btn)

        layout.addLayout(btn_layout)

    def _refresh_ports(self) -> None:
        """Scan and populate available serial ports."""
        current = self._port.currentText()
        self._port.clear()
        try:
            from serial_session import SerialSession
            ports = SerialSession.list_ports()
        except Exception:
            ports = []
        self._port.addItems(ports)
        if current:
            self._port.setEditText(current)

    def _on_connect(self) -> None:
        """Validate inputs and accept."""
        port = self._port.currentText().strip()
        if not port:
            QMessageBox.warning(self, "Error", "Please select or enter a serial port.")
            return
        self.accept()

    def get_connection_params(self) -> dict:
        """Return the connection parameters as a dict."""
        parity_map = {"None": "N", "Even": "E", "Odd": "O", "Mark": "M", "Space": "S"}
        stopbits_map = {"1": 1, "1.5": 1.5, "2": 2}

        return {
            "port": self._port.currentText().strip(),
            "baudrate": self._baud.currentData() or 115200,
            "bytesize": self._databits.value(),
            "parity": parity_map.get(self._parity.currentText(), "N"),
            "stopbits": stopbits_map.get(self._stopbits.currentText(), 1),
            "flow_control": self._flow_control.isChecked(),
        }
