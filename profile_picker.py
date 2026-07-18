"""
Profile picker dialog for OmniTerm.

Shows a list of available shell profiles and lets the user pick one.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt

from config import Config, Profile


class ProfilePickerDialog(QDialog):
    """Modal dialog that presents available profiles and returns the selected name."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self._selected: str | None = None

        self.setWindowTitle("Select Shell Profile")
        self.setMinimumWidth(350)
        self.setMinimumHeight(250)

        layout = QVBoxLayout(self)

        label = QLabel("Choose a shell to open:")
        layout.addWidget(label)

        self._list = QListWidget()
        for name, profile in config.profiles.items():
            item = QListWidgetItem(f"{name}  —  {profile.command}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._list.addItem(item)

        # Select the default profile
        default = config.default_profile
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == default:
                self._list.setCurrentItem(item)
                break

        self._list.itemDoubleClicked.connect(self._on_accept)
        layout.addWidget(self._list)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        open_btn = QPushButton("Open")
        open_btn.setDefault(True)
        open_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(open_btn)

        layout.addLayout(btn_layout)

    def _on_accept(self, item=None) -> None:
        current = self._list.currentItem()
        if current:
            self._selected = current.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def get_selected(self) -> str | None:
        """Return the selected profile name, or None if cancelled."""
        return self._selected

    def get_command(self) -> tuple[str, list[str]]:
        """Return the (command, args) for the selected profile."""
        if self._selected:
            profile = self._config.get_profile(self._selected)
            if profile:
                return profile.command, profile.args
        return "cmd.exe", []
