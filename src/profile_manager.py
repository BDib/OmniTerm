"""
Profile management dialog for OmniTerm.

Provides a UI to add, edit, and delete shell profiles.
Each profile can be configured with name, command, args, working dir, and admin flag.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QAbstractItemView, QLineEdit, QCheckBox,
    QMessageBox, QLabel, QWidget, QFormLayout, QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from config import Config, Profile


class ProfileEditDialog(QDialog):
    """Dialog for editing a single profile's fields."""

    def __init__(self, name: str = "", profile: Profile | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Profile" if profile else "New Profile")
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        # Name
        self._name_edit = QLineEdit(name)
        layout.addRow("Profile Name:", self._name_edit)

        # Command
        self._cmd_edit = QLineEdit(profile.command if profile else "cmd.exe")
        self._cmd_edit.setPlaceholderText("e.g. cmd.exe, powershell.exe, bash")
        layout.addRow("Command:", self._cmd_edit)

        # Args (space-separated)
        args_str = " ".join(profile.args) if profile and profile.args else ""
        self._args_edit = QLineEdit(args_str)
        self._args_edit.setPlaceholderText("e.g. -NoLogo -NoProfile")
        layout.addRow("Arguments:", self._args_edit)

        # Working Directory
        self._dir_edit = QLineEdit(profile.working_dir if profile and profile.working_dir else "")
        self._dir_edit.setPlaceholderText("Leave empty for default")
        layout.addRow("Working Dir:", self._dir_edit)

        # Admin
        self._admin_cb = QCheckBox("Run as Administrator")
        self._admin_cb.setChecked(profile.admin if profile else False)
        layout.addRow("", self._admin_cb)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> tuple[str, Profile]:
        """Return (name, Profile) from the form."""
        name = self._name_edit.text().strip() or "unnamed"
        args = self._args_edit.text().strip().split()
        working_dir = self._dir_edit.text().strip() or None
        profile = Profile(
            command=self._cmd_edit.text().strip() or "cmd.exe",
            args=args,
            admin=self._admin_cb.isChecked(),
            working_dir=working_dir,
        )
        return name, profile


class ProfileManagerDialog(QDialog):
    """Dialog for managing shell profiles."""

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self.setWindowTitle("Manage Profiles")
        self.setMinimumSize(700, 420)

        layout = QVBoxLayout(self)

        # ── Hint label ──
        hint = QLabel("Double-click a row to edit, or use the buttons below.")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # ── Profile table ──
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Command", "Arguments", "Working Dir", "Admin"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(4, 70)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._edit_profile)
        layout.addWidget(self._table)

        # ── Button row ──
        btn_layout = QHBoxLayout()

        self._add_btn = QPushButton("+ New Profile")
        self._add_btn.clicked.connect(self._add_profile)
        btn_layout.addWidget(self._add_btn)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.clicked.connect(self._edit_profile)
        btn_layout.addWidget(self._edit_btn)

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

        items = [
            name,
            profile.command,
            " ".join(profile.args) if profile.args else "",
            profile.working_dir or "",
        ]
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, col, item)

        # Admin checkbox (read-only display)
        admin_cb = QCheckBox()
        admin_cb.setChecked(profile.admin)
        admin_cb.setEnabled(False)
        cell_widget = QWidget()
        cb_layout = QHBoxLayout(cell_widget)
        cb_layout.addWidget(admin_cb)
        cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        self._table.setCellWidget(row, 4, cell_widget)

    def _add_profile(self):
        """Open the edit dialog to create a new profile."""
        dlg = ProfileEditDialog(parent=self)
        if dlg.exec():
            name, profile = dlg.get_data()
            if name in self._cfg.profiles:
                QMessageBox.warning(self, "Duplicate",
                    f"Profile '{name}' already exists.")
                return
            self._cfg.profiles[name] = profile
            self._add_row(name, profile)

    def _edit_profile(self):
        """Open the edit dialog for the selected profile."""
        row = self._table.currentRow()
        if row < 0:
            return

        old_name = self._table.item(row, 0).text()
        profile = self._cfg.profiles.get(old_name)
        if not profile:
            return

        dlg = ProfileEditDialog(name=old_name, profile=profile, parent=self)
        if dlg.exec():
            new_name, new_profile = dlg.get_data()
            # Remove old entry if name changed
            if new_name != old_name:
                self._cfg.profiles.pop(old_name, None)
            self._cfg.profiles[new_name] = new_profile

            # Refresh table
            self._load_profiles()

    def _duplicate_profile(self):
        """Duplicate the selected profile."""
        row = self._table.currentRow()
        if row < 0:
            return

        old_name = self._table.item(row, 0).text()
        old_profile = self._cfg.profiles.get(old_name)
        if not old_profile:
            return

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
            args = args_str.split()
            working_dir = self._table.item(row, 3).text().strip() or None

            cell = self._table.cellWidget(row, 4)
            admin = False
            if cell:
                cb = cell.findChild(QCheckBox)
                if cb:
                    admin = cb.isChecked()

            self._cfg.profiles[name] = Profile(
                command=command, args=args, admin=admin,
                working_dir=working_dir)

        self._cfg.save()
        self.accept()
