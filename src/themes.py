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

# ─── Extra Themes ───────────────────────────────────────────────────────────

MONOKAI = Theme(
    name="Monokai",
    background="#272822",
    foreground="#F8F8F2",
    cursor="#F8F8F2",
    selection_bg="#49483E",
    selection_fg="#F8F8F2",
    ansi={
        "black": "#272822",
        "red": "#F92672",
        "green": "#A6E22E",
        "yellow": "#F4BF75",
        "blue": "#66D9EF",
        "magenta": "#AE81FF",
        "cyan": "#A1EFE4",
        "white": "#F8F8F2",
        "bright_black": "#75715E",
        "bright_red": "#F92672",
        "bright_green": "#A6E22E",
        "bright_yellow": "#F4BF75",
        "bright_blue": "#66D9EF",
        "bright_magenta": "#AE81FF",
        "bright_cyan": "#A1EFE4",
        "bright_white": "#F9F8F5",
    },
)

DRACULA = Theme(
    name="Dracula",
    background="#282A36",
    foreground="#F8F8F2",
    cursor="#F8F8F2",
    selection_bg="#44475A",
    selection_fg="#F8F8F2",
    ansi={
        "black": "#21222C",
        "red": "#FF5555",
        "green": "#50FA7B",
        "yellow": "#F1FA8C",
        "blue": "#BD93F9",
        "magenta": "#FF79C6",
        "cyan": "#8BE9FD",
        "white": "#F8F8F2",
        "bright_black": "#6272A4",
        "bright_red": "#FF6E6E",
        "bright_green": "#69FF94",
        "bright_yellow": "#FFFFA5",
        "bright_blue": "#D6ACFF",
        "bright_magenta": "#FF92DF",
        "bright_cyan": "#A4FFFF",
        "bright_white": "#FFFFFF",
    },
)

NORD = Theme(
    name="Nord",
    background="#2E3440",
    foreground="#D8DEE9",
    cursor="#D8DEE9",
    selection_bg="#434C5E",
    selection_fg="#D8DEE9",
    ansi={
        "black": "#3B4252",
        "red": "#BF616A",
        "green": "#A3BE8C",
        "yellow": "#EBCB8B",
        "blue": "#81A1C1",
        "magenta": "#B48EAD",
        "cyan": "#88C0D0",
        "white": "#E5E9F0",
        "bright_black": "#4C566A",
        "bright_red": "#BF616A",
        "bright_green": "#A3BE8C",
        "bright_yellow": "#EBCB8B",
        "bright_blue": "#81A1C1",
        "bright_magenta": "#B48EAD",
        "bright_cyan": "#8FBCBB",
        "bright_white": "#ECEFF4",
    },
)

GITHUB_DARK = Theme(
    name="GitHub Dark",
    background="#0D1117",
    foreground="#C9D1D9",
    cursor="#C9D1D9",
    selection_bg="#1F6FEB33",
    selection_fg="#C9D1D9",
    ansi={
        "black": "#484F58",
        "red": "#FF7B72",
        "green": "#3FB950",
        "yellow": "#D29922",
        "blue": "#58A6FF",
        "magenta": "#BC8CFF",
        "cyan": "#39C5CF",
        "white": "#C9D1D9",
        "bright_black": "#6E7681",
        "bright_red": "#FFA198",
        "bright_green": "#56D364",
        "bright_yellow": "#E3B341",
        "bright_blue": "#79C0FF",
        "bright_magenta": "#D2A8FF",
        "bright_cyan": "#56D4DD",
        "bright_white": "#F0F6FC",
    },
)

CATPPUCCIN_MOCHA = Theme(
    name="Catppuccin Mocha",
    background="#1E1E2E",
    foreground="#CDD6F4",
    cursor="#F5E0DC",
    selection_bg="#45475A",
    selection_fg="#CDD6F4",
    ansi={
        "black": "#45475A",
        "red": "#F38BA8",
        "green": "#A6E3A1",
        "yellow": "#F9E2AF",
        "blue": "#89B4FA",
        "magenta": "#F5C2E7",
        "cyan": "#94E2D5",
        "white": "#BAC2DE",
        "bright_black": "#585B70",
        "bright_red": "#F38BA8",
        "bright_green": "#A6E3A1",
        "bright_yellow": "#F9E2AF",
        "bright_blue": "#89B4FA",
        "bright_magenta": "#F5C2E7",
        "bright_cyan": "#94E2D5",
        "bright_white": "#A6ADC8",
    },
)

Tomorrow_Night = Theme(
    name="Tomorrow Night",
    background="#1D1F21",
    foreground="#C5C8C6",
    cursor="#C5C8C6",
    selection_bg="#282A2E",
    selection_fg="#C5C8C6",
    ansi={
        "black": "#1D1F21",
        "red": "#CC6666",
        "green": "#B5BD68",
        "yellow": "#F0C674",
        "blue": "#81A2BE",
        "magenta": "#B294BB",
        "cyan": "#8ABEB7",
        "white": "#C5C8C6",
        "bright_black": "#969896",
        "bright_red": "#CC6666",
        "bright_green": "#B5BD68",
        "bright_yellow": "#F0C674",
        "bright_blue": "#81A2BE",
        "bright_magenta": "#B294BB",
        "bright_cyan": "#8ABEB7",
        "bright_white": "#FFFFFF",
    },
)

GRUVBOX_DARK = Theme(
    name="Gruvbox Dark",
    background="#282828",
    foreground="#EBDBB2",
    cursor="#EBDBB2",
    selection_bg="#3C3836",
    selection_fg="#EBDBB2",
    ansi={
        "black": "#282828",
        "red": "#CC241D",
        "green": "#98971A",
        "yellow": "#D79921",
        "blue": "#458588",
        "magenta": "#B16286",
        "cyan": "#689D6A",
        "white": "#A89984",
        "bright_black": "#928374",
        "bright_red": "#FB4934",
        "bright_green": "#B8BB26",
        "bright_yellow": "#FABD2F",
        "bright_blue": "#83A598",
        "bright_magenta": "#D3869B",
        "bright_cyan": "#8EC07C",
        "bright_white": "#EBDBB2",
    },
)

Tokyo_Night = Theme(
    name="Tokyo Night",
    background="#1A1B26",
    foreground="#C0CAF5",
    cursor="#C0CAF5",
    selection_bg="#33467C",
    selection_fg="#C0CAF5",
    ansi={
        "black": "#15161E",
        "red": "#F7768E",
        "green": "#9ECE6A",
        "yellow": "#E0AF68",
        "blue": "#7AA2F7",
        "magenta": "#BB9AF7",
        "cyan": "#7DCFFF",
        "white": "#A9B1D6",
        "bright_black": "#414868",
        "bright_red": "#F7768E",
        "bright_green": "#9ECE6A",
        "bright_yellow": "#E0AF68",
        "bright_blue": "#7AA2F7",
        "bright_magenta": "#BB9AF7",
        "bright_cyan": "#7DCFFF",
        "bright_white": "#C0CAF5",
    },
)

Rosé_Pine = Theme(
    name="Rosé Pine",
    background="#191724",
    foreground="#E0DEF4",
    cursor="#E0DEF4",
    selection_bg="#2A283E",
    selection_fg="#E0DEF4",
    ansi={
        "black": "#26233A",
        "red": "#EB6F92",
        "green": "#31748F",
        "yellow": "#F6C177",
        "blue": "#9CCFD8",
        "magenta": "#C4A7E7",
        "cyan": "#EBBCBA",
        "white": "#E0DEF4",
        "bright_black": "#6E6A86",
        "bright_red": "#EB6F92",
        "bright_green": "#31748F",
        "bright_yellow": "#F6C177",
        "bright_blue": "#9CCFD8",
        "bright_magenta": "#C4A7E7",
        "bright_cyan": "#EBBCBA",
        "bright_white": "#E0DEF4",
    },
)

Zenburn = Theme(
    name="Zenburn",
    background="#3C3836",
    foreground="#D5C4A1",
    cursor="#D5C4A1",
    selection_bg="#504945",
    selection_fg="#D5C4A1",
    ansi={
        "black": "#3C3836",
        "red": "#CC241D",
        "green": "#98971A",
        "yellow": "#D79921",
        "blue": "#458588",
        "magenta": "#B16286",
        "cyan": "#689D6A",
        "white": "#D5C4A1",
        "bright_black": "#928374",
        "bright_red": "#FB4934",
        "bright_green": "#B8BB26",
        "bright_yellow": "#FABD2F",
        "bright_blue": "#83A598",
        "bright_magenta": "#D3869B",
        "bright_cyan": "#8EC07C",
        "bright_white": "#EBDBB2",
    },
)


# ─── Registry ──────────────────────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "campbell": CAMPBELL,
    "solarized_dark": SOLARIZED_DARK,
    "one_half_dark": ONE_HALF_DARK,
    "monokai": MONOKAI,
    "dracula": DRACULA,
    "nord": NORD,
    "github_dark": GITHUB_DARK,
    "catppuccin_mocha": CATPPUCCIN_MOCHA,
    "tomorrow_night": Tomorrow_Night,
    "gruvbox_dark": GRUVBOX_DARK,
    "tokyo_night": Tokyo_Night,
    "rose_pine": Rosé_Pine,
    "zenburn": Zenburn,
}


def get_theme(name: str) -> Theme:
    """Return the theme matching *name*, falling back to Campbell."""
    return THEMES.get(name.lower(), CAMPBELL)


def list_themes() -> list[str]:
    """Return sorted list of available theme names."""
    return sorted(THEMES.keys())
