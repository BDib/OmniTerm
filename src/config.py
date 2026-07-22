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

VERSION = "2.1.6"


def _appdata_dir() -> Path:
    """Return %APPDATA%/OmniTerm, creating it if it doesn't exist."""
    base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    d = base / "OmniTerm"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_config_path() -> Path:
    """Resolve the config file location.

    Search order:
      1. OMNITERM_CONFIG environment variable
      2. Same directory as the executable/script
      3. %APPDATA%/OmniTerm/settings.toml
    Returns the first path that exists, or a path to create on first run.
    """
    env = os.environ.get("OMNITERM_CONFIG")
    if env:
        p = Path(env)
        if p.is_file():
            return p

    # Determine where to look — next to the exe, next to the script, or CWD
    if getattr(sys, "frozen", False):
        # Frozen (PyInstaller or Nuitka): look next to the exe
        exe_dir = Path(sys.executable).parent
    else:
        # Dev mode: look next to the script, then CWD
        exe_dir = Path(__file__).resolve().parent.parent  # src/ → project root

    # 1. Next to the exe / script
    candidate = exe_dir / "settings.toml"
    if candidate.is_file():
        return candidate

    # 2. In CWD (for onefile builds that extract to temp)
    cwd_candidate = Path(os.getcwd()) / "settings.toml"
    if cwd_candidate.is_file():
        return cwd_candidate

    # 3. %APPDATA%/OmniTerm/
    appdata_candidate = _appdata_dir() / "settings.toml"
    if appdata_candidate.is_file():
        return appdata_candidate

    # Not found — return CWD path so it gets created on first run
    return cwd_candidate


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
    """A named shell profile (e.g., PowerShell, WSL)."""
    command: str = "cmd.exe"
    args: list[str] = field(default_factory=list)
    admin: bool = False
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
        """Load configuration from a TOML file.

        If the file doesn't exist, creates it with sensible defaults.
        If the file exists but is malformed, falls back to defaults.
        """
        if path is None:
            path = _default_config_path()
        else:
            path = Path(path)

        cfg = cls()

        if not path.is_file():
            # Create settings.toml with sensible defaults including profiles
            cfg = cls._defaults()
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                cfg.save(path)
            except Exception:
                pass  # non-critical — defaults still work
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
                admin=bool(data.get("admin", False)),
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

        # If no profiles were loaded, use defaults
        if not cfg.profiles:
            defaults = cls._defaults()
            cfg.profiles = defaults.profiles
            cfg.default_profile = defaults.default_profile

        return cfg

    @classmethod
    def get_config_path(cls) -> Path:
        """Return the resolved config file path."""
        return _default_config_path()

    @classmethod
    def _defaults(cls) -> "Config":
        """Return a Config with all default profiles and settings."""
        cfg = cls()
        cfg.profiles = {
            "cmd": Profile(command="cmd.exe"),
            "powershell": Profile(
                command="powershell.exe",
                args=["-NoLogo", "-NoProfile"],
            ),
            "pwsh": Profile(
                command="pwsh.exe",
                args=["-NoLogo", "-NoProfile"],
            ),
            "cmd_admin": Profile(command="cmd.exe", admin=True),
            "powershell_admin": Profile(
                command="powershell.exe",
                args=["-NoLogo", "-NoProfile"],
                admin=True,
            ),
            "wsl": Profile(command="wsl.exe"),
        }
        cfg.default_profile = "cmd"
        return cfg

    def save(self, path: str | Path | None = None) -> None:
        """Save configuration back to TOML."""
        import toml
        if path is None:
            path = self.get_config_path()
        else:
            path = Path(path)

        data: dict[str, Any] = {}

        data["behavior"] = {"rtl_threshold": self.behavior.rtl_threshold}

        data["ui"] = {
            "opacity": self.ui.opacity,
            "font_family": self.ui.font_family,
            "font_size": self.ui.font_size,
            "theme": self.ui.theme,
            "cursor_style": self.ui.cursor_style,
            "cursor_blink": self.ui.cursor_blink,
        }

        data["default_profile"] = self.default_profile

        data["profiles"] = {}
        for name, p in self.profiles.items():
            prof: dict[str, Any] = {"command": p.command}
            if p.args:
                prof["args"] = p.args
            if p.admin:
                prof["admin"] = True
            if p.working_dir:
                prof["working_dir"] = p.working_dir
            if p.font_size is not None:
                prof["font_size"] = p.font_size
            if p.theme:
                prof["theme"] = p.theme
            data["profiles"][name] = prof

        data["keybindings"] = {}
        for kb in self.keybindings:
            data["keybindings"][kb.shortcut] = kb.action

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            toml.dump(data, f)

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
