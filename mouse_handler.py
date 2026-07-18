"""
Mouse event handling for OmniTerm.

Encodes Qt mouse events into xterm-compatible escape sequences and sends
them to the PTY when mouse tracking is enabled.

Supported modes:
  - Normal tracking (\x1b[?1000h): sends button press/release.
  - Button-event tracking (\x1b[?1002h): also sends drag events.
  - Any-event tracking (\x1b[?1003h): sends all motion events.

Mouse escape format: ESC [ M Cb Cx Cy
  - Cb = button + modifiers (encoded as a single byte)
  - Cx = column + 32
  - Cy = row + 32
"""

from __future__ import annotations

from enum import IntFlag


class MouseMode(IntFlag):
    NONE = 0
    NORMAL = 1       # \x1b[?1000h
    BUTTON = 2       # \x1b[?1002h
    ANY = 4          # \x1b[?1003h


class MouseHandler:
    """Tracks mouse mode state and encodes events for the PTY."""

    def __init__(self):
        self.mode: MouseMode = MouseMode.NONE
        self._enabled: dict[int, bool] = {
            1000: False,  # normal tracking
            1002: False,  # button-event tracking
            1003: False,  # any-event tracking
            1006: False,  # SGR extended mode (not yet implemented)
        }

    @property
    def is_active(self) -> bool:
        return self.mode != MouseMode.NONE

    def set_mode(self, mode_num: int, enabled: bool) -> None:
        """Enable or disable a mouse mode (called by CSI ? h / l)."""
        if mode_num in self._enabled:
            self._enabled[mode_num] = enabled
            self._recompute_mode()

    def _recompute_mode(self) -> None:
        if self._enabled.get(1003):
            self.mode = MouseMode.ANY
        elif self._enabled.get(1002):
            self.mode = MouseMode.BUTTON
        elif self._enabled.get(1000):
            self.mode = MouseMode.NORMAL
        else:
            self.mode = MouseMode.NONE

    def encode_press(self, col: int, row: int, button: int, shift: bool = False,
                     ctrl: bool = False, alt: bool = False) -> str | None:
        """Encode a mouse button press as an escape sequence.

        Args:
            col, row: 1-based cursor position.
            button: 0=left, 1=middle, 2=right, 64=scroll_up, 65=scroll_down.
            shift, ctrl, alt: Modifier state.

        Returns:
            The encoded escape sequence, or None if mouse mode is inactive.
        """
        if not self.is_active:
            return None

        # For scroll buttons (64+), use directly; for regular buttons, mask to 2 bits
        if button >= 64:
            cb = button
        else:
            cb = button & 0x03
        if shift:
            cb |= 0x04
        if ctrl:
            cb |= 0x08
        if alt:
            cb |= 0x10

        return self._encode(cb, col, row)

    def encode_release(self, col: int, row: int, button: int) -> str | None:
        """Encode a mouse button release."""
        if not self.is_active:
            return None

        # Release: set bit 5 (32) + button bits
        cb = 32 | (button & 0x03)
        return self._encode(cb, col, row)

    def encode_motion(self, col: int, row: int, button: int = 0,
                      shift: bool = False, ctrl: bool = False,
                      alt: bool = False) -> str | None:
        """Encode mouse motion (drag)."""
        if self.mode not in (MouseMode.BUTTON, MouseMode.ANY):
            return None

        cb = 32 | (button & 0x03)  # motion bit set
        if shift:
            cb |= 0x04
        if ctrl:
            cb |= 0x08
        if alt:
            cb |= 0x10

        return self._encode(cb, col, row)

    @staticmethod
    def _encode(cb: int, col: int, row: int) -> str:
        """Encode the final escape sequence."""
        # Encode col and row as single bytes (offset by 32)
        cx = min(223, max(1, col)) + 32
        cy = min(223, max(1, row)) + 32
        return f"\x1b[M{chr(cb)}{chr(cx)}{chr(cy)}"
