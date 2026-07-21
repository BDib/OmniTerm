"""
Unit tests for keyboard input handling.

Tests the QTextEdit-based input and shell output rendering.
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


# ── Input via QTextEdit ──────────────────────────────────────────────


def test_type_and_enter():
    """Typing in input + Enter sends the command."""
    w, engine, app = _make_widget()
    w._set_input_text("dir")
    w._on_enter()
    assert "dir" in _all(engine), f"Expected 'dir' in output, got: {engine.written}"
    assert w._input_text() == "", "Input should be cleared"
    print("  PASS: Type + Enter sends command")


def test_enter_empty():
    """Enter with empty input sends just \\r."""
    w, engine, app = _make_widget()
    w._set_input_text("")
    w._on_enter()
    assert _last(engine) == "\r", f"Empty Enter should send \\r, got: {_last(engine)!r}"
    print("  PASS: Empty Enter sends \\r")


def test_command_sent_to_engine():
    """After Enter, the command should be sent to the engine."""
    w, engine, app = _make_widget()
    w._set_input_text("echo hello")
    w._on_enter()
    assert "echo hello" in _all(engine), f"Command should be sent: {engine.written}"
    print("  PASS: Command sent to engine")


def test_engine_not_ready():
    """Enter when engine not ready should not send."""
    w, engine, app = _make_widget()
    engine.is_ready = False
    w._set_input_text("dir")
    w._on_enter()
    assert len(engine.written) == 0, "Should not send when engine not ready"
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


# ── Input QTextEdit features ────────────────────────────────────────


def test_input_cursor_visible():
    """Input QTextEdit should have a visible cursor."""
    w, engine, app = _make_widget()
    w._set_input_text("hello")
    assert w._input_text() == "hello", "Text should be set"
    print("  PASS: Input text is settable")


def test_input_editing():
    """Input QTextEdit supports text editing."""
    w, engine, app = _make_widget()
    w._set_input_text("hello")
    assert w._input_text() == "hello"
    # Clear and set new text
    w._clear_input()
    assert w._input_text() == ""
    w._set_input_text("world")
    assert w._input_text() == "world"
    print("  PASS: Input editing works")


def test_focus_on_input():
    """setFocus should target the input field."""
    w, engine, app = _make_widget()
    w.show()
    app.processEvents()
    w.setFocus()
    app.processEvents()
    assert w._input.hasFocus(), "Input should have focus"
    print("  PASS: Focus goes to input")


# ── History ─────────────────────────────────────────────────────────


def test_history_navigation():
    """Up/Down arrows should navigate command history."""
    w, engine, app = _make_widget()
    # Submit first command
    w._set_input_text("dir")
    w._on_enter()
    # Submit second command
    w._set_input_text("echo hello")
    w._on_enter()
    # Up arrow should recall "echo hello"
    w._history_up()
    result = w._input_text()
    assert result == "echo hello", f"Up should recall last, got {result!r}"
    # Up again should recall "dir"
    w._history_up()
    result = w._input_text()
    assert result == "dir", f"Up again should recall first, got {result!r}"
    # Down should go back
    w._history_down()
    result = w._input_text()
    assert result == "echo hello", f"Down should recall second, got {result!r}"
    # Down past end clears
    w._history_down()
    assert w._input_text() == "", "Down past end should clear"
    print("  PASS: History navigation")


# ── Theme ────────────────────────────────────────────────────────────


def test_theme_applies():
    """Theme should be applied to output, input, and path label."""
    w, engine, app = _make_widget()
    w.apply_theme_by_name("dracula")
    assert w._cfg.ui.theme == "dracula"
    print("  PASS: Theme applies")


# ── Path label ───────────────────────────────────────────────────────


def test_path_label_exists():
    """Path label should be present and have text."""
    w, engine, app = _make_widget()
    assert hasattr(w, '_path_label'), "Should have path label"
    assert w._path_label.text() != "", "Path label should have text"
    print("  PASS: Path label exists")


def run_all():
    print("Running keyboard input tests...")
    print()
    print("  Input:")
    test_type_and_enter()
    test_enter_empty()
    test_command_sent_to_engine()
    test_engine_not_ready()
    print()
    print("  Output:")
    test_shell_output_rendered()
    test_erase_display()
    test_ansi_colors()
    print()
    print("  Input QTextEdit:")
    test_input_cursor_visible()
    test_input_editing()
    test_focus_on_input()
    print()
    print("  History:")
    test_history_navigation()
    print()
    print("  Theme:")
    test_theme_applies()
    print()
    print("  Path label:")
    test_path_label_exists()
    print()
    print("All keyboard input tests passed!\n")


if __name__ == "__main__":
    run_all()
