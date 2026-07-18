"""
Unit tests for the mouse handler and scroll buffer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mouse_handler import MouseHandler, MouseMode
from scroll_buffer import ScrollBuffer, TextSpan


# ─── Mouse Handler Tests ───────────────────────────────────────────────────

def test_mouse_default_inactive():
    """Mouse should be inactive by default."""
    m = MouseHandler()
    assert not m.is_active
    assert m.mode == MouseMode.NONE
    print("  PASS: Default mouse is inactive")


def test_mouse_enable_normal():
    """Enabling mode 1000 should set NORMAL tracking."""
    m = MouseHandler()
    m.set_mode(1000, True)
    assert m.is_active
    assert m.mode == MouseMode.NORMAL
    print("  PASS: Enable normal mouse tracking")


def test_mouse_enable_button():
    """Enabling mode 1002 should set BUTTON tracking."""
    m = MouseHandler()
    m.set_mode(1002, True)
    assert m.mode == MouseMode.BUTTON
    print("  PASS: Enable button-event tracking")


def test_mouse_enable_any():
    """Enabling mode 1003 should set ANY tracking."""
    m = MouseHandler()
    m.set_mode(1003, True)
    assert m.mode == MouseMode.ANY
    print("  PASS: Enable any-event tracking")


def test_mouse_disable():
    """Disabling all modes should return to NONE."""
    m = MouseHandler()
    m.set_mode(1000, True)
    m.set_mode(1000, False)
    assert m.mode == MouseMode.NONE
    assert not m.is_active
    print("  PASS: Disable mouse tracking")


def test_mouse_priority():
    """ANY > BUTTON > NORMAL in mode priority."""
    m = MouseHandler()
    m.set_mode(1000, True)
    assert m.mode == MouseMode.NORMAL
    m.set_mode(1002, True)
    assert m.mode == MouseMode.BUTTON
    m.set_mode(1003, True)
    assert m.mode == MouseMode.ANY
    m.set_mode(1003, False)
    assert m.mode == MouseMode.BUTTON
    m.set_mode(1002, False)
    assert m.mode == MouseMode.NORMAL
    print("  PASS: Mode priority correct")


def test_encode_press_inactive():
    """No sequence when mouse is inactive."""
    m = MouseHandler()
    seq = m.encode_press(1, 1, 0)
    assert seq is None
    print("  PASS: No encode when inactive")


def test_encode_press_active():
    """Active mouse should produce a valid escape sequence."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_press(5, 10, 0)
    assert seq is not None
    assert seq.startswith("\x1b[M")
    assert len(seq) == 6  # ESC [ M Cb Cx Cy
    print("  PASS: Encode press produces valid sequence")


def test_encode_press_with_shift():
    """Shift modifier should set bit 2 in Cb."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_press(1, 1, 0, shift=True)
    cb = ord(seq[3])  # ESC [ M Cb ...
    assert cb & 0x04  # shift bit
    print("  PASS: Encode press with shift modifier")


def test_encode_press_with_ctrl():
    """Ctrl modifier should set bit 3 in Cb."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_press(1, 1, 0, ctrl=True)
    cb = ord(seq[3])  # ESC [ M Cb ...
    assert cb & 0x08  # ctrl bit
    print("  PASS: Encode press with ctrl modifier")


def test_encode_release():
    """Release should set bit 5 (32) in Cb."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_release(1, 1, 0)
    assert seq is not None
    cb = ord(seq[3])  # ESC [ M Cb ...
    assert cb & 32  # release bit
    print("  PASS: Encode release sets release bit")


def test_encode_motion_inactive():
    """No motion sequence when mode is NORMAL."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_motion(1, 1)
    assert seq is None  # NORMAL doesn't support motion
    print("  PASS: No motion in NORMAL mode")


def test_encode_motion_active():
    """Motion should produce a sequence in BUTTON/ANY mode."""
    m = MouseHandler()
    m.set_mode(1002, True)
    seq = m.encode_motion(5, 10)
    assert seq is not None
    cb = ord(seq[3])  # ESC [ M Cb ...
    assert cb & 32  # motion bit
    print("  PASS: Encode motion in BUTTON mode")


def test_encode_scroll():
    """Scroll up should encode as button 64."""
    m = MouseHandler()
    m.set_mode(1000, True)
    seq = m.encode_press(1, 1, 64)
    assert seq is not None
    cb = ord(seq[3])  # ESC [ M Cb ...
    assert cb == 64
    print("  PASS: Encode scroll up")


# ─── Scroll Buffer Tests ──────────────────────────────────────────────────

def test_scroll_buffer_empty():
    """Empty buffer should have 0 lines."""
    buf = ScrollBuffer()
    assert buf.line_count == 0
    assert buf.get_visible_lines(10) == []
    print("  PASS: Empty buffer")


def test_scroll_buffer_append():
    """Appending lines should increase line count."""
    buf = ScrollBuffer()
    buf.append_line([TextSpan(text="hello")])
    buf.append_line([TextSpan(text="world")])
    assert buf.line_count == 2
    print("  PASS: Append lines")


def test_scroll_buffer_capacity():
    """Buffer should respect capacity limit."""
    buf = ScrollBuffer(capacity=5)
    for i in range(10):
        buf.append_line([TextSpan(text=f"line {i}")])
    assert buf.line_count == 5
    # Should contain the last 5 lines
    lines = buf.get_visible_lines(10)
    assert lines[0][0].text == "line 5"
    assert lines[-1][0].text == "line 9"
    print("  PASS: Capacity limit")


def test_scroll_buffer_viewport():
    """Viewport should show the correct slice of lines."""
    buf = ScrollBuffer(capacity=100)
    for i in range(20):
        buf.append_line([TextSpan(text=f"line {i}")])
    # Default viewport (bottom): should show last 10
    visible = buf.get_visible_lines(10)
    assert len(visible) == 10
    assert visible[0][0].text == "line 10"
    assert visible[-1][0].text == "line 19"
    print("  PASS: Viewport shows correct slice")


def test_scroll_buffer_scroll_up():
    """Scrolling up should show older lines."""
    buf = ScrollBuffer(capacity=100)
    for i in range(20):
        buf.append_line([TextSpan(text=f"line {i}")])
    buf.scroll_up(5)
    assert buf.viewport_offset == 5
    visible = buf.get_visible_lines(10)
    assert visible[0][0].text == "line 5"
    print("  PASS: Scroll up")


def test_scroll_buffer_scroll_down():
    """Scrolling down should show newer lines."""
    buf = ScrollBuffer(capacity=100)
    for i in range(20):
        buf.append_line([TextSpan(text=f"line {i}")])
    buf.scroll_up(10)
    buf.scroll_down(5)
    assert buf.viewport_offset == 5
    print("  PASS: Scroll down")


def test_scroll_buffer_scroll_to_bottom():
    """Scroll to bottom should reset offset to 0."""
    buf = ScrollBuffer(capacity=100)
    for i in range(20):
        buf.append_line([TextSpan(text=f"line {i}")])
    buf.scroll_up(10)
    buf.scroll_to_bottom()
    assert buf.viewport_offset == 0
    print("  PASS: Scroll to bottom")


def test_scroll_buffer_scroll_to_top():
    """Scroll to top should maximize offset."""
    buf = ScrollBuffer(capacity=100)
    for i in range(20):
        buf.append_line([TextSpan(text=f"line {i}")])
    buf.scroll_to_top()
    assert buf.viewport_offset == 19
    print("  PASS: Scroll to top")


def test_scroll_buffer_clear():
    """Clear should empty the buffer."""
    buf = ScrollBuffer()
    buf.append_line([TextSpan(text="hello")])
    buf.clear()
    assert buf.line_count == 0
    assert buf.viewport_offset == 0
    print("  PASS: Clear buffer")


def test_scroll_buffer_to_plain_text():
    """to_plain_text should return all lines joined."""
    buf = ScrollBuffer()
    buf.append_line([TextSpan(text="hello"), TextSpan(text=" ")])
    buf.append_line([TextSpan(text="world")])
    text = buf.to_plain_text()
    assert "hello " in text
    assert "world" in text
    assert "\n" in text
    print("  PASS: to_plain_text")


def test_scroll_buffer_get_line():
    """get_line should return a specific line by index."""
    buf = ScrollBuffer()
    buf.append_line([TextSpan(text="first")])
    buf.append_line([TextSpan(text="second")])
    line = buf.get_line(0)
    assert line is not None
    assert line[0].text == "first"
    assert buf.get_line(99) is None
    print("  PASS: get_line by index")


def test_scroll_buffer_append_updates_offset():
    """Appending while scrolled up should maintain relative position."""
    buf = ScrollBuffer(capacity=100)
    for i in range(10):
        buf.append_line([TextSpan(text=f"line {i}")])
    buf.scroll_up(5)
    assert buf.viewport_offset == 5
    buf.append_line([TextSpan(text="new line")])
    assert buf.viewport_offset == 6  # shifted by 1
    print("  PASS: Append maintains viewport offset")


def run_all():
    print("Running mouse handler tests...")
    test_mouse_default_inactive()
    test_mouse_enable_normal()
    test_mouse_enable_button()
    test_mouse_enable_any()
    test_mouse_disable()
    test_mouse_priority()
    test_encode_press_inactive()
    test_encode_press_active()
    test_encode_press_with_shift()
    test_encode_press_with_ctrl()
    test_encode_release()
    test_encode_motion_inactive()
    test_encode_motion_active()
    test_encode_scroll()
    print("All mouse handler tests passed!\n")

    print("Running scroll buffer tests...")
    test_scroll_buffer_empty()
    test_scroll_buffer_append()
    test_scroll_buffer_capacity()
    test_scroll_buffer_viewport()
    test_scroll_buffer_scroll_up()
    test_scroll_buffer_scroll_down()
    test_scroll_buffer_scroll_to_bottom()
    test_scroll_buffer_scroll_to_top()
    test_scroll_buffer_clear()
    test_scroll_buffer_to_plain_text()
    test_scroll_buffer_get_line()
    test_scroll_buffer_append_updates_offset()
    print("All scroll buffer tests passed!\n")


if __name__ == "__main__":
    run_all()
