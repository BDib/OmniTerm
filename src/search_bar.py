"""
Search bar widget for OmniTerm.

Provides a Ctrl+F search bar that highlights matches in the terminal output.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor


class SearchBar(QWidget):
    """A floating search bar that appears at the bottom of the terminal."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = None  # QTextEdit to search in
        self._last_query = ""

        self.setFixedHeight(32)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self._label = QLabel("Find:")
        layout.addWidget(self._label)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search...")
        self._input.returnPressed.connect(self.find_next)
        self._input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._input)

        self._count_label = QLabel("")
        layout.addWidget(self._count_label)

        self._prev_btn = QPushButton("\u25B2")  # up triangle
        self._prev_btn.setFixedWidth(24)
        self._prev_btn.clicked.connect(self.find_prev)
        layout.addWidget(self._prev_btn)

        self._next_btn = QPushButton("\u25BC")  # down triangle
        self._next_btn.setFixedWidth(24)
        self._next_btn.clicked.connect(self.find_next)
        layout.addWidget(self._next_btn)

        self._close_btn = QPushButton("\u2715")
        self._close_btn.setFixedWidth(24)
        self._close_btn.clicked.connect(self.close_bar)
        layout.addWidget(self._close_btn)

        self.setVisible(False)

    def attach(self, target) -> None:
        """Attach to a QTextEdit widget for searching."""
        self._target = target

    def open_bar(self) -> None:
        """Show the search bar and focus the input."""
        self.setVisible(True)
        self._input.setFocus()
        self._input.selectAll()

    def close_bar(self) -> None:
        """Hide the search bar and clear highlights."""
        self._clear_highlights()
        self.setVisible(False)
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
        self._find(direction=1)

    def _find(self, direction: int = 1) -> None:
        """Find next/prev match and select it."""
        if not self._target or not self._last_query:
            return

        cursor = self._target.textCursor()

        # If we have a selection, start searching from its end/start
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
        """Update the match count label."""
        if not self._target or not self._last_query:
            return

        # Count all occurrences
        cursor = self._target.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        count = 0
        while True:
            cursor = self._target.document().find(
                self._last_query, cursor.position(),
                QTextCursor.SelectionFlag.FindCaseSensitively,
            )
            if cursor.isNull():
                break
            count += 1

        # Show current position
        all_cursors = self._target.extraSelections()
        total = len(all_cursors)
        current = 0
        if total > 0:
            sel_cursor = self._target.textCursor()
            for i, es in enumerate(all_cursors):
                if es.cursor.selectionStart() == sel_cursor.selectionStart():
                    current = i + 1
                    break
            self._count_label.setText(f"{current}/{total}")
        else:
            self._count_label.setText("No match")
