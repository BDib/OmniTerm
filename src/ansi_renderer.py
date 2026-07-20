"""
ANSI span → QTextCharFormat renderer for OmniTerm.

Takes a list of ``Span`` objects from ``ansi_parser.parse_ansi`` and
replays them into a ``QTextEdit`` with proper styling.
"""

from __future__ import annotations

from ansi_parser import Span, SpanKind, SGRState, indexed_to_rgb
from themes import Theme

from PyQt6.QtGui import QTextCharFormat, QColor, QFont


def _color_from_sgr(sgr_color: int | None, sgr_rgb: tuple[int, int, int] | None,
                     theme: Theme, is_fg: bool) -> QColor | None:
    """Resolve an SGR color value to a QColor."""
    if sgr_rgb:
        return QColor(sgr_rgb[0], sgr_rgb[1], sgr_rgb[2])
    if sgr_color is not None:
        if sgr_color in indexed_to_rgb:
            r, g, b = indexed_to_rgb[sgr_color]
            return QColor(r, g, b)
        # Fallback: map to the nearest theme ANSI color
        ansi_names = [
            "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
        ]
        if 0 <= sgr_color < 8:
            name = ansi_names[sgr_color]
            if is_fg and name in theme.ansi:
                return QColor(theme.ansi[name])
        elif 8 <= sgr_color < 16:
            name = f"bright_{ansi_names[sgr_color - 8]}"
            if is_fg and name in theme.ansi:
                return QColor(theme.ansi[name])
    return None


def span_to_format(sgr: SGRState, theme: Theme) -> QTextCharFormat:
    """Convert an ``SGRState`` to a ``QTextCharFormat``."""
    fmt = QTextCharFormat()

    # Foreground color
    fg = _color_from_sgr(sgr.fg, sgr.fg_rgb, theme, is_fg=True)
    if fg:
        fmt.setForeground(fg)
    elif sgr.inverse:
        # Invert: fg becomes theme background
        fmt.setForeground(QColor(theme.background))

    # Background color
    bg = _color_from_sgr(sgr.bg, sgr.bg_rgb, theme, is_fg=False)
    if bg:
        fmt.setBackground(bg)
    elif sgr.inverse:
        # Invert: bg becomes theme foreground
        fmt.setBackground(QColor(theme.foreground))

    # Font weight
    if sgr.bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if sgr.dim:
        fmt.setForeground(QColor("#808080"))

    # Font style
    if sgr.italic:
        fmt.setFontItalic(True)
    if sgr.underline:
        fmt.setFontUnderline(True)
    if sgr.strikethrough:
        fmt.setFontStrikeOut(True)

    return fmt
