"""
Search bar widget for OmniTerm.

Provides a Ctrl+F / F3 search bar that highlights matches in the terminal output.
Positioned at the bottom of the output QTextEdit.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor


class SearchBar(QWidget):
    """Search bar that sits at the bottom of the output QTextEdit."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = parent  # The output QTextEdit we search in
        self._last_query = ""

        self.setFixedHeight(32)
        self.setStyleSheet(
            "SearchBar { background: #2a2a2a; border-top: 1px solid #444; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        self._label = QLabel("Find:")
        self._label.setStyleSheet("color: #aaa;")
        layout.addWidget(self._label)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search in output...")
        self._input.setFixedWidth(250)
        self._input.returnPressed.connect(self.find_next)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #aaa; min-width: 60px;")
        layout.addWidget(self._count_label)

        self._prev_btn = QPushButton("\u25B2")
        self._prev_btn.setFixedSize(24, 24)
        self._prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("\u25BC")
        self._next_btn.setFixedSize(24, 24)
        self._next_btn.clicked.connect(self.find_next)
        layout.addWidget(self._next_btn)

        layout.addStretch()

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.clicked.connect(self.close_bar)
        layout.addWidget(self._close_btn)

        self.setVisible(False)

    def resizeEvent(self, event):
        """Keep the search bar at the bottom of the parent QTextEdit."""
        super().resizeEvent(event)
        if self._target:
            pw = self._target.width()
            self.setFixedWidth(pw)
            self.move(0, self._target.height() - self.height())

    def open_bar(self) -> None:
        """Show the search bar, position it, and focus the input."""
        if self._target:
            self.setFixedWidth(self._target.width())
            self.move(0, self._target.height() - self.height())
        self.setVisible(True)
        self._input.setFocus()
        self._input.selectAll()
        # If there's already text, search immediately
        if self._input.text():
            self._on_text_changed(self._input.text())

    def close_bar(self) -> None:
        """Hide the search bar and clear highlights."""
        self._clear_highlights()
        self.setVisible(False)
        if self._target:
            self._target.setFocus()
        self.closed.emit()

    def find_next(self) -> None:
        """Find the next occurrence of the search text."""
        self._find(direction=1)

    def find_prev(self) -> None:
        """Find the previous occurrence."""
        self._find(direction=-1)

    def _on_text_changed(self, text: str) -> None:
        """Re-highlight all matches when the search text changes."""
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

        flags = QTextCursor.SelectionFlag.FindCaseSensitively
        if direction < 0:
            flags |= QTextCursor.SelectionFlag.FindBackward

        found = self._target.find(self._last_query, flags)

        if found:
            self._update_count()
        else:
            # Wrap around
            cursor.movePosition(
                QTextCursor.MoveOperation.Start if direction > 0
                else QTextCursor.MoveOperation.End
            )
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
            cursor = self._target.document().find(
                text, cursor.position(),
                QTextCursor.SelectionFlag.FindCaseSensitively,
            )
            if cursor.isNull():
                break
            extra_sel = QTextEdit.ExtraSelection()
            extra_sel.format = fmt
            extra_sel.cursor = cursor
            extra_selections.append(extra_sel)
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
        cursor = self._target.textCursor()
        saved_pos = cursor.selectionStart() if cursor.hasSelection() else cursor.position()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        total = 0
        while True:
            cursor = self._target.document().find(
                self._last_query, cursor.position(),
                QTextCursor.SelectionFlag.FindCaseSensitively,
            )
            if cursor.isNull():
                break
            total += 1

        # Find current position
        sel_cursor = self._target.textCursor()
        current = 0
        if sel_cursor.hasSelection():
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            idx = 0
            while True:
                cursor = self._target.document().find(
                    self._last_query, cursor.position(),
                    QTextCursor.SelectionFlag.FindCaseSensitively,
                )
                if cursor.isNull():
                    break
                idx += 1
                if cursor.selectionStart() == sel_cursor.selectionStart():
                    current = idx
                    break

        if total > 0:
            self._count_label.setText(f"{current}/{total}")
        else:
            self._count_label.setText("No match")
