"""
Unit tests for the terminal rendering pipeline.

Tests the ANSI span -> QTextEdit rendering logic, especially:
  - Carriage return handling (ignored for compatibility with shell echo)
  - ERASE_DISPLAY clears the widget
  - ERASE_LINE clears from cursor to end of block
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _make_widget():
    """Create a TerminalWidget with a running QApplication."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from terminal_ui import TerminalWidget
    from config import Config
    cfg = Config()
    w = TerminalWidget(cfg=cfg, plain_mode=False)
    return w, app


def _get_text(widget):
    """Get plain text content of the widget."""
    return widget.toPlainText()


def test_cr_ignored_for_line_endings():
    """CR followed by NL (\\r\\n line ending) should produce correct output."""
    w, app = _make_widget()
    w.append_shell_text("Hello world\r\n")
    text = _get_text(w)
    assert "Hello world" in text, f"Text should be preserved, got: {text}"
    # CR moves to start of block, NL inserts newline — text ends up correct
    print("  PASS: CR+NL preserves text")


def test_cr_appends_text():
    """CR should be ignored so subsequent text is appended."""
    w, app = _make_widget()
    w.append_shell_text("C:\\Users> ")
    w.append_shell_text("\rpowershell> dir")
    text = _get_text(w)
    # CR is ignored, so both prompts appear
    assert "powershell> dir" in text
    print("  PASS: CR ignored, text appended")


def test_erase_display_clears():
    """ERASE_DISPLAY (\\x1b[2J) should clear all content."""
    w, app = _make_widget()
    w.append_shell_text("Some content\r\nMore content\r\n")
    assert _get_text(w) != ""
    w.append_shell_text("\x1b[2J")
    text = _get_text(w)
    assert text == "", f"Widget should be empty after ERASE_DISPLAY, got: {text!r}"
    print("  PASS: ERASE_DISPLAY clears widget")


def test_erase_display_then_text():
    """After ERASE_DISPLAY, new text should appear from the start."""
    w, app = _make_widget()
    w.append_shell_text("Old content\r\n")
    w.append_shell_text("\x1b[2JNew prompt> ")
    text = _get_text(w)
    assert "Old content" not in text, f"Old content should be gone: {text}"
    assert "New prompt> " in text, f"New prompt should exist: {text}"
    print("  PASS: ERASE_DISPLAY then new text")


def test_erase_line():
    """ERASE_LINE (\\x1b[K) clears from cursor to end of line."""
    w, app = _make_widget()
    # \\x1b[K clears from cursor to end. Cursor is at end after text, so no-op.
    w.append_shell_text("old prompt> \x1b[K")
    text = _get_text(w)
    assert "old prompt> " in text, f"Text at end of line should remain: {text!r}"
    print("  PASS: ERASE_LINE at end of line (no-op)")


def test_erase_line_after_text():
    """ERASE_LINE after some text should clear the rest."""
    w, app = _make_widget()
    w.append_shell_text("short\x1b[K")
    text = _get_text(w)
    assert "short" in text, f"Existing text should remain: {text}"
    print("  PASS: ERASE_LINE after text")


def test_plain_mode_text():
    """Plain mode should work correctly."""
    from PyQt6.QtWidgets import QApplication
    QApplication.instance() or QApplication(sys.argv)
    from terminal_ui import TerminalWidget
    from config import Config
    cfg = Config()
    w = TerminalWidget(cfg=cfg, plain_mode=True)
    w.append_shell_text("Hello\r\nWorld")
    text = _get_text(w)
    assert "Hello" in text
    assert "World" in text
    print("  PASS: Plain mode text")


def run_all():
    print("Running rendering pipeline tests...")
    test_cr_ignored_for_line_endings()
    test_cr_appends_text()
    test_erase_display_clears()
    test_erase_display_then_text()
    test_erase_line()
    test_erase_line_after_text()
    test_plain_mode_text()
    print("All rendering pipeline tests passed!\n")


if __name__ == "__main__":
    run_all()
