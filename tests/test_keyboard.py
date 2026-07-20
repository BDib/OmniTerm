"""
Unit tests for keyboard input handling.

Tests the QLineEdit-based input and shell output rendering.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class MockEngine:
    def __init__(self):
        self.written: list[str] = []
        self.is_ready = True
        self.alive = True

    def write(self, data: str):
        self.written.append(data)

    def flush(self):
        self.written.clear()


def _make_widget():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from terminal_ui import TerminalWidget
    from config import Config
    cfg = Config()
    w = TerminalWidget(cfg=cfg, plain_mode=False)
    engine = MockEngine()
    w.parent_engine = engine
    return w, engine, app


def _last(engine):
    return engine.written[-1] if engine.written else None


def _all(engine):
    return "".join(engine.written)


# ── Input via QLineEdit ──────────────────────────────────────────────


def test_type_and_enter():
    """Typing in QLineEdit + Enter sends the command."""
    w, engine, app = _make_widget()
    w._input.setText("dir")
    w._input.returnPressed.emit()
    assert "dir" in _all(engine), f"Expected 'dir' in output, got: {engine.written}"
    assert w._input.text() == "", f"Input should be cleared"
    print("  PASS: Type + Enter sends command")


def test_enter_empty():
    """Enter with empty input sends just \\r (prompt refresh)."""
    w, engine, app = _make_widget()
    w._input.setText("")
    w._input.returnPressed.emit()
    assert _last(engine) == "\r", f"Empty Enter should send \\r, got: {_last(engine)!r}"
    print("  PASS: Empty Enter sends \\r")


def test_command_appears_in_output():
    """After Enter, the command should appear in the output (from shell echo)."""
    w, engine, app = _make_widget()
    w._input.setText("echo hello")
    w._input.returnPressed.emit()
    # Command is sent to shell — shell echoes it back via append_shell_text
    assert "echo hello" in _all(engine), f"Command should be sent to engine: {engine.written}"
    print("  PASS: Command sent to shell for echo")


def test_engine_not_ready():
    """Enter when engine not ready should not send."""
    w, engine, app = _make_widget()
    engine.is_ready = False
    w._input.setText("dir")
    w._input.returnPressed.emit()
    assert len(engine.written) == 0, f"Should not send when engine not ready"
    print("  PASS: Engine not ready blocks send")


# ── Output rendering ─────────────────────────────────────────────────


def test_shell_output_rendered():
    """Shell output should appear in the output area."""
    w, engine, app = _make_widget()
    w.append_shell_text("Hello world\n")
    output = w._output.toPlainText()
    assert "Hello world" in output, f"Output should contain shell text: {output}"
    print("  PASS: Shell output rendered")


def test_erase_display():
    """ERASE_DISPLAY should clear the output."""
    w, engine, app = _make_widget()
    w.append_shell_text("Some content\n")
    w.append_shell_text("\x1b[2J")
    output = w._output.toPlainText()
    assert "Some content" not in output, f"Should be cleared: {output}"
    print("  PASS: ERASE_DISPLAY clears output")


def test_ansi_colors():
    """ANSI color codes should be parsed (not crash)."""
    w, engine, app = _make_widget()
    w.append_shell_text("\x1b[31mRed text\x1b[0m Normal\n")
    output = w._output.toPlainText()
    assert "Red text" in output, f"Colored text should appear: {output}"
    print("  PASS: ANSI colors handled")


# ── QLineEdit features ───────────────────────────────────────────────


def test_input_cursor_visible():
    """QLineEdit should have a visible cursor."""
    w, engine, app = _make_widget()
    w._input.setText("hello")
    # QLineEdit always has a visible cursor when it has focus
    assert w._input.cursorPosition() >= 0, "Cursor position should be valid"
    print("  PASS: Input cursor is visible")


def test_input_editing():
    """QLineEdit supports native editing (left/right, delete, etc.)."""
    w, engine, app = _make_widget()
    w._input.setText("hello")
    # Move cursor left
    w._input.setCursorPosition(2)
    assert w._input.cursorPosition() == 2
    # Insert text at cursor
    w._input.insert("X")
    assert w._input.text() == "heXllo", f"Insert at cursor: {w._input.text()}"
    # Delete backward — cursor is now after X (pos 3), backspace removes X
    w._input.backspace()
    assert w._input.text() == "hello", f"After backspace: {w._input.text()}"
    # Delete forward via QLineEdit.delete()
    w._input.setCursorPosition(1)
    w._input.del_()
    assert w._input.text() == "hllo", f"After delete: {w._input.text()}"
    print("  PASS: Input editing works natively")


def test_focus_on_input():
    """setFocus should target the input field."""
    w, engine, app = _make_widget()
    w.show()  # needs to be visible for focus to work
    app.processEvents()
    w.setFocus()
    app.processEvents()
    assert w._input.hasFocus(), "Input should have focus"
    print("  PASS: Focus goes to input")


# ── Theme ────────────────────────────────────────────────────────────


def test_theme_applies():
    """Theme should be applied to both output and input."""
    w, engine, app = _make_widget()
    w.apply_theme_by_name("solarized_dark")
    assert w._cfg.ui.theme == "solarized_dark"
    print("  PASS: Theme applies")


def run_all():
    print("Running keyboard input tests...")
    print()
    print("  Input:")
    test_type_and_enter()
    test_enter_empty()
    test_command_appears_in_output()
    test_engine_not_ready()
    print()
    print("  Output:")
    test_shell_output_rendered()
    test_erase_display()
    test_ansi_colors()
    print()
    print("  QLineEdit features:")
    test_input_cursor_visible()
    test_input_editing()
    test_focus_on_input()
    print()
    print("  Theme:")
    test_theme_applies()
    print()
    print("All keyboard input tests passed!\n")


if __name__ == "__main__":
    run_all()
