"""
Profile management dialog for OmniTerm.

Provides a UI to add, edit, and delete shell profiles.
Each profile can be configured with command, args, and Run As Admin flag.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QLineEdit, QCheckBox,
    QMessageBox, QLabel, QComboBox, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import Config, Profile


class ProfileManagerDialog(QDialog):
    """Dialog for managing shell profiles."""

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("Manage Profiles")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # ── Profile table ──
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Name", "Command", "Args", "Admin"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 70)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        layout.addWidget(self._table)

        # ── Button row ──
        btn_layout = QHBoxLayout()

        self._add_btn = QPushButton("+ Add Profile")
        self._add_btn.clicked.connect(self._add_profile)
        btn_layout.addWidget(self._add_btn)

        self._dup_btn = QPushButton("Duplicate")
        self._dup_btn.clicked.connect(self._duplicate_profile)
        btn_layout.addWidget(self._dup_btn)

        self._del_btn = QPushButton("Remove")
        self._del_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(self._del_btn)

        btn_layout.addStretch()

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save_profiles)
        btn_layout.addWidget(self._save_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(btn_layout)

        # Load data
        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from config into the table."""
        self._table.setRowCount(0)
        for name, profile in sorted(self._cfg.profiles.items()):
            self._add_row(name, profile)

    def _add_row(self, name: str, profile: Profile):
        """Add a row to the table."""
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Name
        name_item = QTableWidgetItem(name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, 0, name_item)

        # Command
        self._table.setItem(row, 1, QTableWidgetItem(profile.command))

        # Args (comma-separated)
        args_str = ", ".join(profile.args) if profile.args else ""
        self._table.setItem(row, 2, QTableWidgetItem(args_str))

        # Admin checkbox
        admin_cb = QCheckBox()
        admin_cb.setChecked(profile.admin)
        admin_cb.stateChanged.connect(lambda state, r=row: self._on_admin_changed(r, state))
        cell_widget = QWidget()
        cb_layout = QHBoxLayout(cell_widget)
        cb_layout.addWidget(admin_cb)
        cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        self._table.setCellWidget(row, 3, cell_widget)

    def _on_admin_changed(self, row: int, state: int):
        """Handle admin checkbox change."""
        pass  # State is read when saving

    def _add_profile(self):
        """Add a new empty profile."""
        # Find a unique name
        base = "new_profile"
        name = base
        counter = 1
        while name in self._cfg.profiles:
            name = f"{base}_{counter}"
            counter += 1

        profile = Profile(command="cmd.exe")
        self._cfg.profiles[name] = profile
        self._add_row(name, profile)

    def _duplicate_profile(self):
        """Duplicate the selected profile."""
        row = self._table.currentRow()
        if row < 0:
            return

        old_name = self._table.item(row, 0).text()
        old_profile = self._cfg.profiles.get(old_name)
        if not old_profile:
            return

        # Find a unique name
        base = f"{old_name}_copy"
        name = base
        counter = 1
        while name in self._cfg.profiles:
            name = f"{base}_{counter}"
            counter += 1

        new_profile = Profile(
            command=old_profile.command,
            args=list(old_profile.args),
            admin=old_profile.admin,
            working_dir=old_profile.working_dir,
        )
        self._cfg.profiles[name] = new_profile
        self._add_row(name, new_profile)

    def _delete_profile(self):
        """Delete the selected profile."""
        row = self._table.currentRow()
        if row < 0:
            return

        name = self._table.item(row, 0).text()
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cfg.profiles.pop(name, None)
            self._table.removeRow(row)

    def _save_profiles(self):
        """Save all profiles back to config."""
        self._cfg.profiles.clear()

        for row in range(self._table.rowCount()):
            name = self._table.item(row, 0).text()
            command = self._table.item(row, 1).text() or "cmd.exe"
            args_str = self._table.item(row, 2).text() or ""
            args = [a.strip() for a in args_str.split(",") if a.strip()]

            # Get admin checkbox state
            admin = False
            cell = self._table.cellWidget(row, 3)
            if cell:
                cb = cell.findChild(QCheckBox)
                if cb:
                    admin = cb.isChecked()

            self._cfg.profiles[name] = Profile(
                command=command, args=args, admin=admin)

        # Persist to file
        self._cfg.save()
        self.accept()
