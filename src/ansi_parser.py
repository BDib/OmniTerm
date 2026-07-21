"""
Lightweight ANSI escape sequence parser for OmniTerm.

Parses CSI sequences (SGR styling, cursor movement, screen/line clearing)
and emits a list of ``Span`` objects that the UI layer renders with
``QTextCharFormat``.

Design goals:
  - No external dependencies (pure Python regex + dataclasses).
  - Handles the most common VT100/xterm sequences used by cmd.exe,
    PowerShell, and WSL.
  - Gracefully ignores sequences it doesn't understand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto


# ─── Span: a run of styled or control text ─────────────────────────────────

class SpanKind(Enum):
    TEXT = auto()
    NEWLINE = auto()
    CARRIAGE_RETURN = auto()
    TAB = auto()
    BELL = auto()
    BACKSPACE = auto()
    CURSOR_UP = auto()
    CURSOR_DOWN = auto()
    CURSOR_FORWARD = auto()
    CURSOR_BACK = auto()
    CURSOR_HOME = auto()
    CURSOR_POS = auto()       # \x1b[row;colH
    ERASE_DISPLAY = auto()    # \x1b[2J  or  \x1b[J
    ERASE_LINE = auto()       # \x1b[2K  or  \x1b[K
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    SAVE_CURSOR = auto()
    RESTORE_CURSOR = auto()
    SET_TITLE = auto()        # \x1b]0;...\x07
    MOUSE_MODE = auto()       # \x1b[?1000h / \x1b[?1000l (DEC private mode)


@dataclass
class SGRState:
    """Current SGR (Select Graphic Rendition) attributes."""
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    inverse: bool = False
    strikethrough: bool = False
    fg: int | None = None       # None = default; 0-255 for indexed; tuple for RGB
    bg: int | None = None
    fg_rgb: tuple[int, int, int] | None = None
    bg_rgb: tuple[int, int, int] | None = None
    reset: bool = False

    def copy(self) -> "SGRState":
        return SGRState(
            bold=self.bold, dim=self.dim, italic=self.italic,
            underline=self.underline, inverse=self.inverse,
            strikethrough=self.strikethrough,
            fg=self.fg, bg=self.bg,
            fg_rgb=self.fg_rgb, bg_rgb=self.bg_rgb,
        )

    def apply_params(self, params: list[int]) -> None:
        """Apply a list of SGR parameter codes."""
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self.__init__()  # reset all
            elif p == 1:
                self.bold = True
            elif p == 2:
                self.dim = True
            elif p == 3:
                self.italic = True
            elif p == 4:
                self.underline = True
            elif p == 7:
                self.inverse = True
            elif p == 9:
                self.strikethrough = True
            elif p == 22:
                self.bold = False
                self.dim = False
            elif p == 23:
                self.italic = False
            elif p == 24:
                self.underline = False
            elif p == 27:
                self.inverse = False
            elif p == 29:
                self.strikethrough = False
            # Foreground: 30-37, 38, 39
            elif p == 39:
                self.fg = None
                self.fg_rgb = None
            elif 30 <= p <= 37:
                self.fg = p - 30
                self.fg_rgb = None
            elif p == 38:
                i += 1
                self.fg, self.fg_rgb = self._parse_color(params, i)
                i += self._color_skip(params, i) - 1
            # Background: 40-47, 48, 49
            elif p == 49:
                self.bg = None
                self.bg_rgb = None
            elif 40 <= p <= 47:
                self.bg = p - 40
                self.bg_rgb = None
            elif p == 48:
                i += 1
                self.bg, self.bg_rgb = self._parse_color(params, i)
                i += self._color_skip(params, i) - 1
            i += 1

    # ── helpers ──

    @staticmethod
    def _parse_color(params: list[int], i: int) -> tuple[int | None, tuple[int, int, int] | None]:
        if i >= len(params):
            return None, None
        mode = params[i]
        if mode == 5 and i + 1 < len(params):
            return params[i + 1], None  # 256-color
        if mode == 2 and i + 3 < len(params):
            return None, (params[i + 1], params[i + 2], params[i + 3])  # RGB
        return None, None

    @staticmethod
    def _color_skip(params: list[int], i: int) -> int:
        if i >= len(params):
            return 0
        mode = params[i]
        if mode == 5:
            return 2  # mode + index
        if mode == 2:
            return 4  # mode + r + g + b
        return 1


# 8-bit ANSI color → RGB mapping (standard xterm colors)
indexed_to_rgb: dict[int, tuple[int, int, int]] = {
    0:  (0, 0, 0),       1:  (128, 0, 0),     2:  (0, 128, 0),     3:  (128, 128, 0),
    4:  (0, 0, 128),     5:  (128, 0, 128),    6:  (0, 128, 128),   7:  (192, 192, 192),
    8:  (128, 128, 128), 9:  (255, 0, 0),      10: (0, 255, 0),     11: (255, 255, 0),
    12: (0, 0, 255),     13: (255, 0, 255),    14: (0, 255, 255),   15: (255, 255, 255),
    # 16-231: 6×6×6 color cube
    **{(16 + 36*r + 6*g + b): (r*51, g*51, b*51)
       for r in range(6) for g in range(6) for b in range(6)},
    # 232-255: grayscale ramp
    **{i: (8 + (i - 232) * 10, 8 + (i - 232) * 10, 8 + (i - 232) * 10)
       for i in range(232, 256)},
}


@dataclass
class Span:
    kind: SpanKind
    text: str = ""
    sgr: SGRState = field(default_factory=SGRState)
    row: int = 1
    col: int = 1


# ─── Regex patterns ────────────────────────────────────────────────────────

# CSI: ESC [ ... final_byte  (including ? prefix for DEC private modes)
_CSI_RE = re.compile(r"\x1b\[(\?)?([0-9;]*)([A-Za-z])")
# OSC: ESC ] num ; text BEL  or  ESC ] num ; text ST
_OSC_RE = re.compile(r"\x1b\]([0-9]);(.*?)(?:\x07|\x1b\\)")
# Control characters
_CTRL_RE = re.compile(r"[\x00-\x1f]")


# ─── Parser ────────────────────────────────────────────────────────────────

def parse_ansi(data: str) -> list[Span]:
    """Parse *data* into a list of ``Span`` objects.

    The caller iterates these spans and maps them to ``QTextCharFormat``
    + cursor operations for rendering.
    """
    spans: list[Span] = []
    sgr = SGRState()
    i = 0
    n = len(data)

    while i < n:
        ch = data[i]

        # ── OSC sequences (title, etc.) ──
        if ch == "\x1b" and i + 1 < n and data[i + 1] == "]":
            m = _OSC_RE.match(data, i)
            if m:
                spans.append(Span(kind=SpanKind.SET_TITLE, text=m.group(2)))
                i = m.end()
                continue

        # ── CSI sequences (including DEC private modes) ──
        if ch == "\x1b" and i + 1 < n and data[i + 1] == "[":
            m = _CSI_RE.match(data, i)
            if m:
                is_private = m.group(1) == "?"
                param_str = m.group(2) or ""
                final = m.group(3)
                params = _parse_params(param_str)
                if is_private and final in ("h", "l"):
                    # DEC private mode: \x1b[?<num>h  or  \x1b[?<num>l
                    for p in params:
                        spans.append(Span(
                            kind=SpanKind.MOUSE_MODE,
                            text=f"{p},{final}",
                            sgr=SGRState(),
                        ))
                else:
                    spans.extend(_handle_csi(params, final, sgr))
                i = m.end()
                continue

        # ── Control characters ──
        if ch == "\x1b":
            i += 1
            continue
        if ch == "\r":
            spans.append(Span(kind=SpanKind.CARRIAGE_RETURN, sgr=sgr))
            i += 1
            continue
        if ch == "\n":
            spans.append(Span(kind=SpanKind.NEWLINE, sgr=sgr))
            i += 1
            continue
        if ch == "\t":
            spans.append(Span(kind=SpanKind.TAB, sgr=sgr))
            i += 1
            continue
        if ch == "\b":
            spans.append(Span(kind=SpanKind.BACKSPACE, sgr=sgr))
            i += 1
            continue
        if ch == "\x07":
            spans.append(Span(kind=SpanKind.BELL, sgr=sgr))
            i += 1
            continue

        # Skip other control characters
        if ord(ch) < 0x20:
            i += 1
            continue

        # ── Printable text — accumulate runs ──
        start = i
        while i < n and data[i] >= " " and data[i] not in ("\x1b", "\r", "\n", "\t", "\b", "\x07"):
            i += 1
        if i > start:
            spans.append(Span(kind=SpanKind.TEXT, text=data[start:i], sgr=sgr.copy()))

    return spans


def _parse_params(param_str: str) -> list[int]:
    """Parse a CSI parameter string like ``'1;5'`` into ``[1, 5]``."""
    if not param_str:
        return []
    try:
        return [int(p) if p else 0 for p in param_str.split(";")]
    except ValueError:
        return []


def _handle_csi(params: list[int], final: str, sgr: SGRState) -> list[Span]:
    """Dispatch a CSI sequence to the appropriate span(s)."""
    p = params[0] if params else 0

    # ── SGR (Select Graphic Rendition) ──
    if final == "m":
        sgr.apply_params(params)
        return []

    # ── Cursor movement ──
    if final == "A":
        return [Span(kind=SpanKind.CURSOR_UP, sgr=sgr, row=max(1, p))]
    if final == "B":
        return [Span(kind=SpanKind.CURSOR_DOWN, sgr=sgr, row=max(1, p))]
    if final == "C":
        return [Span(kind=SpanKind.CURSOR_FORWARD, sgr=sgr, col=max(1, p))]
    if final == "D":
        return [Span(kind=SpanKind.CURSOR_BACK, sgr=sgr, col=max(1, p))]
    if final == "H" or final == "f":
        row = params[0] if len(params) > 0 else 1
        col = params[1] if len(params) > 1 else 1
        return [Span(kind=SpanKind.CURSOR_POS, sgr=sgr, row=max(1, row), col=max(1, col))]
    if final == "s":
        return [Span(kind=SpanKind.SAVE_CURSOR, sgr=sgr)]
    if final == "u":
        return [Span(kind=SpanKind.RESTORE_CURSOR, sgr=sgr)]

    # ── Erase ──
    if final == "J":
        return [Span(kind=SpanKind.ERASE_DISPLAY, sgr=sgr)]
    if final == "K":
        return [Span(kind=SpanKind.ERASE_LINE, sgr=sgr)]

    # ── Scroll ──
    if final == "S":
        return [Span(kind=SpanKind.SCROLL_UP, sgr=sgr, row=max(1, p))]
    if final == "T":
        return [Span(kind=SpanKind.SCROLL_DOWN, sgr=sgr, row=max(1, p))]

    # Unknown CSI — ignore
    return []


def strip_ansi(data: str) -> str:
    """Fast ANSI stripping (no parsing).  Used by ``--plain`` mode."""
    data = _CSI_RE.sub("", data)
    data = _OSC_RE.sub("", data)
    data = "".join(c for c in data if ord(c) >= 32 or c in "\n\r\t")
    return data
