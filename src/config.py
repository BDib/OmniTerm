"""
OmniTerm configuration loader.

Reads settings.toml from the project directory (or a user-specified path)
and exposes a typed Config object with sensible defaults.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

VERSION = "1.0.0"


def _appdata_dir() -> Path:
    """Return %APPDATA%/OmniTerm, creating it if it doesn't exist."""
    base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    d = base / "OmniTerm"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_config_path() -> Path:
    """Resolve the config file location."""
    env = os.environ.get("OMNITERM_CONFIG")
    if env:
        p = Path(env)
        if p.is_file():
            return p

    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent  # src/ → project root

    candidate = base / "settings.toml"
    if candidate.is_file():
        return candidate

    candidate = _appdata_dir() / "settings.toml"
    if candidate.is_file():
        return candidate

    return candidate


@dataclass
class UIBehavior:
    rtl_threshold: float = 0.7


@dataclass
class UIConfig:
    opacity: float = 0.98
    font_family: str = "Cascadia Code"
    font_size: int = 14
    theme: str = "campbell"
    cursor_style: str = "bar"
    cursor_blink: bool = True


@dataclass
class Profile:
    """A named shell profile (e.g., PowerShell, WSL, Git Bash)."""
    command: str = "cmd.exe"
    args: list[str] = field(default_factory=list)
    working_dir: str | None = None
    font_size: int | None = None
    theme: str | None = None


@dataclass
class Keybinding:
    """A user-defined keybinding mapping a shortcut to an action."""
    shortcut: str
    action: str


# Built-in actions that keybindings can map to
BUILTIN_ACTIONS = {
    "new_tab", "close_tab", "next_tab", "prev_tab",
    "split_horizontal", "split_vertical",
    "font_bigger", "font_smaller", "font_reset",
    "theme_cycle", "theme_picker",
    "toggle_opacity", "copy", "paste",
    "find", "profile_picker", "ssh_connect",
    "serial_connect", "wsl_connect",
}


@dataclass
class Config:
    behavior: UIBehavior = field(default_factory=UIBehavior)
    ui: UIConfig = field(default_factory=UIConfig)
    profiles: dict[str, Profile] = field(default_factory=dict)
    default_profile: str = "cmd"
    keybindings: list[Keybinding] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load configuration from a TOML file."""
        if path is None:
            path = _default_config_path()
        else:
            path = Path(path)

        cfg = cls()

        if not path.is_file():
            return cfg

        try:
            raw = toml.load(str(path))
        except Exception:
            return cfg

        beh = raw.get("behavior", {})
        cfg.behavior.rtl_threshold = float(
            beh.get("rtl_threshold", cfg.behavior.rtl_threshold)
        )

        ui = raw.get("ui", {})
        cfg.ui.opacity = float(ui.get("opacity", cfg.ui.opacity))
        cfg.ui.font_family = str(ui.get("font_family", cfg.ui.font_family))
        cfg.ui.font_size = int(ui.get("font_size", cfg.ui.font_size))
        cfg.ui.theme = str(ui.get("theme", cfg.ui.theme))
        cfg.ui.cursor_style = str(ui.get("cursor_style", cfg.ui.cursor_style))
        cfg.ui.cursor_blink = bool(ui.get("cursor_blink", cfg.ui.cursor_blink))

        # Profiles
        raw_profiles = raw.get("profiles", {})
        for name, data in raw_profiles.items():
            cfg.profiles[name] = Profile(
                command=str(data.get("command", "cmd.exe")),
                args=list(data.get("args", [])),
                working_dir=data.get("working_dir"),
                font_size=data.get("font_size"),
                theme=data.get("theme"),
            )
        cfg.default_profile = str(raw.get("default_profile", cfg.default_profile))

        # Keybindings
        raw_kb = raw.get("keybindings", {})
        for shortcut, action in raw_kb.items():
            if action in BUILTIN_ACTIONS:
                cfg.keybindings.append(Keybinding(shortcut=shortcut, action=action))

        return cfg

    def get_profile(self, name: str) -> Profile | None:
        """Get a profile by name, or None if not found."""
        return self.profiles.get(name)

    def get_shell_command(self, profile_name: str | None = None) -> tuple[str, list[str]]:
        """Resolve the shell command and args for a profile.

        Returns (command, args) tuple.
        """
        name = profile_name or self.default_profile
        profile = self.profiles.get(name)
        if profile:
            return profile.command, profile.args
        return "cmd.exe", []
