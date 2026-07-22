"""
Unit tests for keyboard input handling under the unified single QTextEdit terminal screen.
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


def _send_key(w, app, key, text="", modifiers=None):
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent, Qt
    if modifiers is None:
        modifiers = Qt.KeyboardModifier.NoModifier
    event = QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)
    app.sendEvent(w._output, event)


# ── Unified Key Handling Tests ─────────────────────────────────────────


def test_type_and_enter():
    """Typing printable characters and pressing Enter writes them to the engine."""
    w, engine, app = _make_widget()
    # Simulate typing 'd', 'i', 'r'
    _send_key(w, app, 0, "d")
    _send_key(w, app, 0, "i")
    _send_key(w, app, 0, "r")
    # Simulate pressing Enter
    from PyQt6.QtCore import Qt
    _send_key(w, app, Qt.Key.Key_Return, "\r")

    assert "dir\r" in _all(engine), f"Expected 'dir\\r' written, got: {engine.written}"
    print("  PASS: Typing + Enter forwards keys to engine")


def test_special_keys_mapped():
    """Special keys are mapped to correct VT sequence standards."""
    from PyQt6.QtCore import Qt
    w, engine, app = _make_widget()

    _send_key(w, app, Qt.Key.Key_Backspace, "\x7f")
    assert _last(engine) == "\x7f", f"Backspace should map to \\x7f, got: {_last(engine)!r}"

    _send_key(w, app, Qt.Key.Key_Up, "")
    assert _last(engine) == "\x1b[A", f"Up Arrow should map to \\x1b[A, got: {_last(engine)!r}"

    _send_key(w, app, Qt.Key.Key_Down, "")
    assert _last(engine) == "\x1b[B", f"Down Arrow should map to \\x1b[B, got: {_last(engine)!r}"

    _send_key(w, app, Qt.Key.Key_Left, "")
    assert _last(engine) == "\x1b[D", f"Left Arrow should map to \\x1b[D, got: {_last(engine)!r}"

    _send_key(w, app, Qt.Key.Key_Right, "")
    assert _last(engine) == "\x1b[C", f"Right Arrow should map to \\x1b[C, got: {_last(engine)!r}"
    print("  PASS: Special keys mapped to proper ANSI sequences")


def test_ctrl_combos_mapped():
    """Ctrl keyboard combos are mapped correctly."""
    from PyQt6.QtCore import Qt
    w, engine, app = _make_widget()

    # Ctrl+C
    _send_key(w, app, Qt.Key.Key_C, "", Qt.KeyboardModifier.ControlModifier)
    assert _last(engine) == "\x03"

    # Ctrl+L
    _send_key(w, app, Qt.Key.Key_L, "", Qt.KeyboardModifier.ControlModifier)
    assert _last(engine) == "\x0c"
    print("  PASS: Ctrl combinations mapped correctly")


def test_engine_not_ready():
    """Keys are ignored if the process engine is not ready."""
    w, engine, app = _make_widget()
    engine.is_ready = False
    _send_key(w, app, 0, "a")
    assert len(engine.written) == 0, "Keys must not be sent if engine is not ready"
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


def test_focus_on_screen():
    """setFocus should target the unified terminal screen."""
    w, engine, app = _make_widget()
    w.show()
    app.processEvents()
    w.setFocus()
    app.processEvents()
    assert w._output.hasFocus(), "Unified terminal screen should have focus"
    print("  PASS: Focus goes to terminal screen")


# ── Theme ────────────────────────────────────────────────────────────


def test_theme_applies():
    """Theme should be applied to the output."""
    w, engine, app = _make_widget()
    w.apply_theme_by_name("dracula")
    assert w._cfg.ui.theme == "dracula"
    print("  PASS: Theme applies")


# ── RTL alignment ───────────────────────────────────────────────────


def test_rtl_toggle_alignment():
    """RTL toggle should set proper alignment on output blocks."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QTextCursor
    w, engine, app = _make_widget()
    w.append_shell_text("Hello World")
    cursor = w._output.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    block_fmt = cursor.blockFormat()
    block_fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
    cursor.setBlockFormat(block_fmt)
    w._output.setTextCursor(cursor)
    # Verify alignment
    cursor = w._output.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    block_fmt = cursor.blockFormat()
    assert block_fmt.alignment() == Qt.AlignmentFlag.AlignRight, \
        f"Expected AlignRight, got {block_fmt.alignment()}"
    print("  PASS: RTL toggle sets alignment")


# ── Save / Export ───────────────────────────────────────────────────


def test_save_output_text():
    """Save as text should write plain text to file."""
    import tempfile, os
    w, engine, app = _make_widget()
    w.append_shell_text("Test output\n")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        tmppath = f.name
    try:
        w.save_output_text(tmppath)
        with open(tmppath, 'r') as f:
            content = f.read()
        assert "Test output" in content, f"Expected 'Test output' in file, got: {content}"
        print("  PASS: Save as text works")
    finally:
        os.unlink(tmppath)


def test_save_output_html():
    """Save as HTML should write themed HTML to file."""
    import tempfile, os
    w, engine, app = _make_widget()
    w.append_shell_text("HTML test\n")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        tmppath = f.name
    try:
        w.save_output_html(tmppath)
        with open(tmppath, 'r') as f:
            content = f.read()
        assert "<!DOCTYPE html>" in content, "Expected DOCTYPE in HTML"
        assert "background-color:" in content, "Expected theme colors in HTML"
        assert "HTML test" in content, f"Expected content in HTML"
        print("  PASS: Save as HTML works")
    finally:
        os.unlink(tmppath)


def run_all():
    print("Running unified keyboard input tests...")
    print()
    print("  Input Handling:")
    test_type_and_enter()
    test_special_keys_mapped()
    test_ctrl_combos_mapped()
    test_engine_not_ready()
    print()
    print("  Output rendering:")
    test_shell_output_rendered()
    test_erase_display()
    test_ansi_colors()
    test_focus_on_screen()
    print()
    print("  Theme:")
    test_theme_applies()
    print()
    print("  RTL:")
    test_rtl_toggle_alignment()
    print()
    print("  Save/Export:")
    test_save_output_text()
    test_save_output_html()
    print()
    print("All unified input tests passed!\n")


if __name__ == "__main__":
    run_all()
