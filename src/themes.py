"""
Built-in color themes for OmniTerm.

Each theme is a dict with:
  - name: display name
  - background / foreground: main colors
  - cursor / selection: UI accent colors
  - ansi: dict of 16 ANSI color names → hex values
"""

from dataclasses import dataclass, field


@dataclass
class Theme:
    name: str
    background: str
    foreground: str
    cursor: str
    selection_bg: str
    selection_fg: str
    ansi: dict[str, str] = field(default_factory=dict)

    def stylesheet(self, font_family: str, font_size: int) -> str:
        """Return a QTextEdit stylesheet for this theme."""
        return f"""
            QTextEdit {{
                background-color: {self.background};
                color: {self.foreground};
                font-family: '{font_family}', 'Consolas', monospace;
                font-size: {font_size}px;
                padding: 10px;
                border: none;
                selection-background-color: {self.selection_bg};
                selection-color: {self.selection_fg};
            }}
        """


# ─── Built-in Themes ───────────────────────────────────────────────────────

CAMPBELL = Theme(
    name="Campbell",
    background="#0C0C0C",
    foreground="#CCCCCC",
    cursor="#FFFFFF",
    selection_bg="#264F78",
    selection_fg="#FFFFFF",
    ansi={
        "black": "#0C0C0C",
        "red": "#C50F1F",
        "green": "#13A10E",
        "yellow": "#C19C00",
        "blue": "#0037DA",
        "magenta": "#881798",
        "cyan": "#3A96DD",
        "white": "#CCCCCC",
        "bright_black": "#767676",
        "bright_red": "#E74856",
        "bright_green": "#16C60C",
        "bright_yellow": "#F9F1A5",
        "bright_blue": "#3B78FF",
        "bright_magenta": "#B4009E",
        "bright_cyan": "#61D6D6",
        "bright_white": "#F2F2F2",
    },
)

SOLARIZED_DARK = Theme(
    name="Solarized Dark",
    background="#002B36",
    foreground="#839496",
    cursor="#93A1A1",
    selection_bg="#073642",
    selection_fg="#93A1A1",
    ansi={
        "black": "#073642",
        "red": "#DC322F",
        "green": "#859900",
        "yellow": "#B58900",
        "blue": "#268BD2",
        "magenta": "#D33682",
        "cyan": "#2AA198",
        "white": "#EEE8D5",
        "bright_black": "#586E75",
        "bright_red": "#CB4B16",
        "bright_green": "#586E75",
        "bright_yellow": "#657B83",
        "bright_blue": "#839496",
        "bright_magenta": "#6C71C4",
        "bright_cyan": "#93A1A1",
        "bright_white": "#FDF6E3",
    },
)

ONE_HALF_DARK = Theme(
    name="One Half Dark",
    background="#282C34",
    foreground="#DCDFE4",
    cursor="#A3B3BF",
    selection_bg="#42464E",
    selection_fg="#DCDFE4",
    ansi={
        "black": "#282C34",
        "red": "#E06C75",
        "green": "#98C379",
        "yellow": "#E5C07B",
        "blue": "#61AFEF",
        "magenta": "#C678DD",
        "cyan": "#56B6C2",
        "white": "#DCDFE4",
        "bright_black": "#5C6370",
        "bright_red": "#E06C75",
        "bright_green": "#98C379",
        "bright_yellow": "#E5C07B",
        "bright_blue": "#61AFEF",
        "bright_magenta": "#C678DD",
        "bright_cyan": "#56B6C2",
        "bright_white": "#FFFFFF",
    },
)


# ─── Registry ──────────────────────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "campbell": CAMPBELL,
    "solarized_dark": SOLARIZED_DARK,
    "one_half_dark": ONE_HALF_DARK,
}


def get_theme(name: str) -> Theme:
    """Return the theme matching *name*, falling back to Campbell."""
    return THEMES.get(name.lower(), CAMPBELL)


def list_themes() -> list[str]:
    """Return sorted list of available theme names."""
    return sorted(THEMES.keys())
