"""
Unit tests for the ANSI escape sequence parser.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ansi_parser import (
    parse_ansi, strip_ansi, SpanKind, SGRState, indexed_to_rgb,
)


def test_plain_text():
    """Plain text should produce a single TEXT span."""
    spans = parse_ansi("hello")
    assert len(spans) == 1
    assert spans[0].kind == SpanKind.TEXT
    assert spans[0].text == "hello"
    print("  PASS: Plain text parsing")


def test_newline():
    """Newlines should produce NEWLINE spans."""
    spans = parse_ansi("a\nb")
    assert len(spans) == 3
    assert spans[0].text == "a"
    assert spans[1].kind == SpanKind.NEWLINE
    assert spans[2].text == "b"
    print("  PASS: Newline parsing")


def test_carriage_return():
    """\\r should produce CARRIAGE_RETURN."""
    spans = parse_ansi("a\rb")
    assert len(spans) == 3
    assert spans[1].kind == SpanKind.CARRIAGE_RETURN
    print("  PASS: Carriage return parsing")


def test_tab():
    """\\t should produce TAB."""
    spans = parse_ansi("a\tb")
    assert len(spans) == 3
    assert spans[1].kind == SpanKind.TAB
    print("  PASS: Tab parsing")


def test_sgr_bold():
    """\\x1b[1m should set bold on the SGR state."""
    spans = parse_ansi("\x1b[1mHello")
    assert len(spans) == 1
    assert spans[0].kind == SpanKind.TEXT
    assert spans[0].text == "Hello"
    assert spans[0].sgr.bold is True
    print("  PASS: SGR bold")


def test_sgr_color():
    """\\x1b[31m should set foreground to red (index 1)."""
    spans = parse_ansi("\x1b[31mRed")
    assert len(spans) == 1
    assert spans[0].sgr.fg == 1
    print("  PASS: SGR color (31 = red)")


def test_sgr_256_color():
    """\\x1b[38;5;208m should set foreground to 256-color index 208."""
    spans = parse_ansi("\x1b[38;5;208mOrange")
    assert len(spans) == 1
    assert spans[0].sgr.fg == 208
    print("  PASS: SGR 256-color")


def test_sgr_rgb_color():
    """\\x1b[38;2;255;128;0m should set foreground RGB."""
    spans = parse_ansi("\x1b[38;2;255;128;0mCustom")
    assert len(spans) == 1
    assert spans[0].sgr.fg_rgb == (255, 128, 0)
    print("  PASS: SGR RGB color")


def test_sgr_reset():
    """\\x1b[0m should reset all attributes."""
    spans = parse_ansi("\x1b[1m\x1b[31mHi\x1b[0mPlain")
    assert spans[0].sgr.bold is True
    assert spans[0].sgr.fg == 1
    assert spans[1].sgr.bold is False
    assert spans[1].sgr.fg is None
    assert spans[1].text == "Plain"
    print("  PASS: SGR reset")


def test_sgr_underline():
    """\\x1b[4m should set underline."""
    spans = parse_ansi("\x1b[4mUnder")
    assert spans[0].sgr.underline is True
    print("  PASS: SGR underline")


def test_sgr_italic():
    """\\x1b[3m should set italic."""
    spans = parse_ansi("\x1b[3mItalic")
    assert spans[0].sgr.italic is True
    print("  PASS: SGR italic")


def test_sgr_inverse():
    """\\x1b[7m should set inverse."""
    spans = parse_ansi("\x1b[7mInverse")
    assert spans[0].sgr.inverse is True
    print("  PASS: SGR inverse")


def test_cursor_up():
    """\\x1b[3A should produce CURSOR_UP with row=3."""
    spans = parse_ansi("\x1b[3A")
    assert len(spans) == 1
    assert spans[0].kind == SpanKind.CURSOR_UP
    assert spans[0].row == 3
    print("  PASS: Cursor up")


def test_cursor_down():
    """\\x1b[2B should produce CURSOR_DOWN with row=2."""
    spans = parse_ansi("\x1b[2B")
    assert spans[0].kind == SpanKind.CURSOR_DOWN
    assert spans[0].row == 2
    print("  PASS: Cursor down")


def test_cursor_position():
    """\\x1b[5;10H should produce CURSOR_POS with row=5, col=10."""
    spans = parse_ansi("\x1b[5;10H")
    assert spans[0].kind == SpanKind.CURSOR_POS
    assert spans[0].row == 5
    assert spans[0].col == 10
    print("  PASS: Cursor position")


def test_erase_display():
    """\\x1b[2J should produce ERASE_DISPLAY."""
    spans = parse_ansi("\x1b[2J")
    assert spans[0].kind == SpanKind.ERASE_DISPLAY
    print("  PASS: Erase display")


def test_erase_line():
    """\\x1b[K should produce ERASE_LINE."""
    spans = parse_ansi("\x1b[K")
    assert spans[0].kind == SpanKind.ERASE_LINE
    print("  PASS: Erase line")


def test_bell():
    """\\x07 should produce BELL."""
    spans = parse_ansi("a\x07b")
    assert spans[1].kind == SpanKind.BELL
    print("  PASS: Bell character")


def test_backspace():
    """\\x08 should produce BACKSPACE."""
    spans = parse_ansi("a\bb")
    assert spans[1].kind == SpanKind.BACKSPACE
    print("  PASS: Backspace character")


def test_osc_title():
    """\\x1b]0;My Title\\x07 should produce SET_TITLE."""
    spans = parse_ansi("\x1b]0;My Title\x07")
    assert spans[0].kind == SpanKind.SET_TITLE
    assert spans[0].text == "My Title"
    print("  PASS: OSC title sequence")


def test_strip_ansi():
    """strip_ansi should remove all escape sequences."""
    text = "\x1b[31mRed\x1b[0m Normal \x1b[1mBold"
    result = strip_ansi(text)
    assert result == "Red Normal Bold"
    print("  PASS: strip_ansi function")


def test_strip_ansi_osc():
    """strip_ansi should remove OSC sequences."""
    text = "\x1b]0;Title\x07Hello"
    result = strip_ansi(text)
    assert result == "Hello"
    print("  PASS: strip_ansi OSC removal")


def test_combined_sequence():
    """A complex real-world sequence should parse correctly."""
    # Typical prompt: colored prompt + reset + text
    text = "\x1b[1;32mC:\\Users>\x1b[0m dir"
    spans = parse_ansi(text)
    # Should have: TEXT(bold+green), TEXT(reset)
    assert len(spans) == 2
    assert spans[0].text == "C:\\Users>"
    assert spans[0].sgr.bold is True
    assert spans[0].sgr.fg == 2  # green
    assert spans[1].text == " dir"
    assert spans[1].sgr.bold is False
    assert spans[1].sgr.fg is None
    print("  PASS: Combined real-world sequence")


def test_indexed_to_rgb_completeness():
    """indexed_to_rgb should have entries for 0-255."""
    for i in range(256):
        assert i in indexed_to_rgb, f"Missing index {i}"
        r, g, b = indexed_to_rgb[i]
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255
    print("  PASS: indexed_to_rgb covers 0-255")


def test_sgr_state_copy():
    """SGRState.copy() should produce an independent copy."""
    s = SGRState(bold=True, fg=3)
    c = s.copy()
    c.bold = False
    c.fg = 5
    assert s.bold is True
    assert s.fg == 3
    print("  PASS: SGRState.copy() independence")


def test_mouse_mode_enable():
    """\\x1b[?1000h should produce MOUSE_MODE span with enable."""
    spans = parse_ansi("\x1b[?1000h")
    assert len(spans) == 1
    assert spans[0].kind == SpanKind.MOUSE_MODE
    assert spans[0].text == "1000,h"
    print("  PASS: Mouse mode enable (DEC private)")


def test_mouse_mode_disable():
    """\\x1b[?1000l should produce MOUSE_MODE span with disable."""
    spans = parse_ansi("\x1b[?1000l")
    assert len(spans) == 1
    assert spans[0].kind == SpanKind.MOUSE_MODE
    assert spans[0].text == "1000,l"
    print("  PASS: Mouse mode disable (DEC private)")


def run_all():
    print("Running ANSI parser tests...")
    test_plain_text()
    test_newline()
    test_carriage_return()
    test_tab()
    test_sgr_bold()
    test_sgr_color()
    test_sgr_256_color()
    test_sgr_rgb_color()
    test_sgr_reset()
    test_sgr_underline()
    test_sgr_italic()
    test_sgr_inverse()
    test_cursor_up()
    test_cursor_down()
    test_cursor_position()
    test_erase_display()
    test_erase_line()
    test_bell()
    test_backspace()
    test_osc_title()
    test_strip_ansi()
    test_strip_ansi_osc()
    test_combined_sequence()
    test_indexed_to_rgb_completeness()
    test_sgr_state_copy()
    test_mouse_mode_enable()
    test_mouse_mode_disable()
    print("All ANSI parser tests passed!\n")


if __name__ == "__main__":
    run_all()
