"""
Scrollback buffer for OmniTerm.

Stores terminal output history in a ring buffer.  The UI renders only the
visible portion, keeping memory bounded while allowing scrollback.

Design:
  - Fixed capacity (configurable, default 10 000 lines).
  - Each line is a list of ``(text, sgr_dict)`` tuples — one per styled span.
  - When the buffer is full, the oldest lines are discarded.
  - The buffer tracks a *viewport offset* (0 = bottom / newest).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextSpan:
    """A single styled span within a line."""
    text: str
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    inverse: bool = False
    strikethrough: bool = False
    fg: int | None = None
    bg: int | None = None
    fg_rgb: tuple[int, int, int] | None = None
    bg_rgb: tuple[int, int, int] | None = None


# A line is a list of TextSpans followed by a newline flag
Line = list[TextSpan]


class ScrollBuffer:
    """Ring-buffer of styled lines with viewport tracking."""

    def __init__(self, capacity: int = 10_000):
        self.capacity = capacity
        self._lines: deque[Line] = deque(maxlen=capacity)
        self._viewport_offset = 0  # 0 = at bottom (newest)

    # ── Write ──────────────────────────────────────────────────────────

    def append_line(self, line: Line | None = None) -> None:
        """Append a completed line to the buffer."""
        self._lines.append(line if line is not None else [])
        if self._viewport_offset > 0:
            self._viewport_offset += 1

    def clear(self) -> None:
        """Clear all lines."""
        self._lines.clear()
        self._viewport_offset = 0

    # ── Read ───────────────────────────────────────────────────────────

    @property
    def line_count(self) -> int:
        return len(self._lines)

    @property
    def viewport_offset(self) -> int:
        """0 = bottom (newest), positive = scrolled up."""
        return self._viewport_offset

    @viewport_offset.setter
    def viewport_offset(self, value: int) -> None:
        self._viewport_offset = max(0, min(value, max(0, self.line_count - 1)))

    def get_visible_lines(self, viewport_height: int) -> list[Line]:
        """Return the lines visible in the viewport."""
        if not self._lines:
            return []
        total = len(self._lines)
        end = total - self._viewport_offset
        start = max(0, end - viewport_height)
        return list(self._lines)[start:end]

    def get_line(self, index: int) -> Line | None:
        """Return a single line by absolute index."""
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return None

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up (view older content)."""
        self._viewport_offset = min(
            self._viewport_offset + lines,
            max(0, self.line_count - 1),
        )

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down (view newer content)."""
        self._viewport_offset = max(0, self._viewport_offset - lines)

    def scroll_to_bottom(self) -> None:
        """Jump to the bottom (newest content)."""
        self._viewport_offset = 0

    def scroll_to_top(self) -> None:
        """Jump to the top (oldest content)."""
        self._viewport_offset = max(0, self.line_count - 1)

    # ── Serialization ──────────────────────────────────────────────────

    def to_plain_text(self) -> str:
        """Export all lines as plain text (no styling)."""
        parts: list[str] = []
        for line in self._lines:
            parts.append("".join(span.text for span in line))
            parts.append("\n")
        return "".join(parts)
