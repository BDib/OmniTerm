"""
Search dialog for OmniTerm.

A popup dialog for finding text in the terminal output.
Supports F3 / Shift+F3 for next/previous match.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QTextEdit,
)
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QTextDocument
from PyQt6.QtCore import Qt


class SearchDialog(QDialog):
    """Popup dialog for finding text in the terminal output."""

    def __init__(self, target: QTextEdit, parent=None):
        super().__init__(parent)
        self._target = target
        self._last_query = ""

        self.setWindowTitle("Find")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setFixedWidth(420)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Find in output...")
        self._input.setClearButtonEnabled(True)
        self._input.returnPressed.connect(self.find_next)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input, 1)

        self._count_label = QLabel("")
        self._count_label.setFixedWidth(60)
        layout.addWidget(self._count_label)

        self._prev_btn = QPushButton("\u25B2 Prev")
        self._prev_btn.setFixedHeight(28)
        self._prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next \u25BC")
        self._next_btn.setFixedHeight(28)
        self._next_btn.setDefault(True)
        self._next_btn.clicked.connect(self.find_next)
        layout.addWidget(self._next_btn)

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(28, 28)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

    def open_dialog(self) -> None:
        """Show the dialog and focus the input."""
        if self.parent():
            pr = self.parent().geometry()
            self.move(pr.right() - self.width() - 20, pr.top() + 40)
        self.show()
        self.raise_()
        self._input.setFocus()
        self._input.selectAll()

    def find_next(self) -> None:
        """Find next occurrence."""
        self._find(direction=1)

    def find_prev(self) -> None:
        """Find previous occurrence."""
        self._find(direction=-1)

    def _on_text_changed(self, text: str) -> None:
        """Highlight all matches and find the first."""
        self._last_query = text
        self._highlight_all(text)
        if text:
            self._find(direction=1)

    def _find(self, direction: int = 1) -> None:
        """Find next/prev match and select it."""
        if not self._target or not self._last_query:
            return

        cursor = self._target.textCursor()

        if cursor.hasSelection():
            if direction > 0:
                cursor.setPosition(cursor.selectionEnd())
            else:
                cursor.setPosition(cursor.selectionStart())
            self._target.setTextCursor(cursor)

        flags = QTextDocument.FindFlag(0)
        if direction < 0:
            flags |= QTextDocument.FindFlag.FindBackward

        found = self._target.find(self._last_query, flags)

        if found:
            self._update_count()
        else:
            # Wrap around
            if direction > 0:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            self._target.setTextCursor(cursor)
            self._target.find(self._last_query, flags)
            self._update_count()

    def _highlight_all(self, text: str) -> None:
        """Highlight all occurrences of *text* in the target."""
        self._clear_highlights()
        if not self._target or not text:
            return

        extra_selections = []
        cursor = self._target.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#4A6FA5"))
        fmt.setForeground(QColor("#FFFFFF"))

        count = 0
        while True:
            found = self._target.document().find(
                text, cursor.position(),
            )
            if found.isNull():
                break
            extra_sel = QTextEdit.ExtraSelection()
            extra_sel.format = fmt
            extra_sel.cursor = found
            extra_selections.append(extra_sel)
            cursor.setPosition(found.selectionEnd())
            count += 1

        self._target.setExtraSelections(extra_selections)
        self._count_label.setText(f"{count} found" if count else "No match")

    def _clear_highlights(self) -> None:
        """Clear all search highlights."""
        if self._target:
            self._target.setExtraSelections([])
            self._count_label.setText("")

    def _update_count(self) -> None:
        """Update the match count label showing current/total."""
        if not self._target or not self._last_query:
            return

        # Count total occurrences
        scan_pos = 0
        total = 0
        while True:
            found = self._target.document().find(self._last_query, scan_pos)
            if found.isNull():
                break
            total += 1
            scan_pos = found.selectionEnd()

        # Find current position
        sel = self._target.textCursor()
        current = 0
        if sel.hasSelection():
            scan_pos = 0
            idx = 0
            while True:
                found = self._target.document().find(self._last_query, scan_pos)
                if found.isNull():
                    break
                idx += 1
                scan_pos = found.selectionEnd()
                if found.selectionStart() == sel.selectionStart():
                    current = idx
                    break

        self._count_label.setText(f"{current}/{total}" if total else "No match")

    def closeEvent(self, event):
        """Clean up highlights when dialog closes."""
        self._clear_highlights()
        super().closeEvent(event)
