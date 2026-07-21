"""
SSH connection dialog for OmniTerm.

Modal dialog for entering SSH connection details: host, port, username,
password, and optional key file.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QPushButton, QFileDialog,
    QCheckBox, QMessageBox,
)


class SSHDialog(QDialog):
    """Modal dialog that collects SSH connection parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SSH Connection")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # ── Form ──
        form = QFormLayout()

        self._host = QLineEdit()
        self._host.setPlaceholderText("hostname or IP address")
        form.addRow("Host:", self._host)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(22)
        form.addRow("Port:", self._port)

        self._username = QLineEdit()
        self._username.setPlaceholderText("root, ubuntu, etc.")
        form.addRow("Username:", self._username)

        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("(leave empty to use key file)")
        form.addRow("Password:", self._password)

        # Key file browser
        key_layout = QHBoxLayout()
        self._key_file = QLineEdit()
        self._key_file.setPlaceholderText("path to private key (optional)")
        key_layout.addWidget(self._key_file)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse_key)
        key_layout.addWidget(browse_btn)
        form.addRow("Key file:", key_layout)

        self._auto_reconnect = QCheckBox("Auto-reconnect on disconnect")
        self._auto_reconnect.setChecked(False)
        form.addRow("", self._auto_reconnect)

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

    def _browse_key(self) -> None:
        """Open a file browser for the key file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select SSH Key File", "",
            "SSH Keys (*.pem *.key *.ppk);;All Files (*)",
        )
        if path:
            self._key_file.setText(path)

    def _on_connect(self) -> None:
        """Validate inputs and accept."""
        host = self._host.text().strip()
        if not host:
            QMessageBox.warning(self, "Error", "Please enter a host address.")
            return

        username = self._username.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a username.")
            return

        self.accept()

    def get_connection_params(self) -> dict:
        """Return the connection parameters as a dict."""
        return {
            "host": self._host.text().strip(),
            "port": self._port.value(),
            "username": self._username.text().strip(),
            "password": self._password.text() or None,
            "key_filename": self._key_file.text().strip() or None,
            "auto_reconnect": self._auto_reconnect.isChecked(),
        }
