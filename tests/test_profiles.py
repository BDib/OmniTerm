"""
Unit tests for profiles, keybindings, search bar, and profile picker.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config, Profile, Keybinding, BUILTIN_ACTIONS


def test_profile_dataclass():
    """Profile should store command, args, and optional settings."""
    p = Profile(command="powershell.exe", args=["-NoLogo"])
    assert p.command == "powershell.exe"
    assert p.args == ["-NoLogo"]
    assert p.working_dir is None
    assert p.font_size is None
    assert p.theme is None
    print("  PASS: Profile dataclass")


def test_profile_with_overrides():
    """Profile should support per-profile font_size and theme."""
    p = Profile(command="cmd.exe", font_size=16, theme="solarized_dark")
    assert p.font_size == 16
    assert p.theme == "solarized_dark"
    print("  PASS: Profile with overrides")


def test_config_loads_profiles():
    """Config should load profiles from settings.toml."""
    cfg = Config.load()
    # The default settings.toml has cmd, powershell, pwsh, wsl, git_bash
    assert "cmd" in cfg.profiles
    assert "powershell" in cfg.profiles
    assert cfg.profiles["cmd"].command == "cmd.exe"
    assert cfg.profiles["powershell"].args == ["-NoLogo", "-NoProfile"]
    print("  PASS: Config loads profiles")


def test_config_default_profile():
    """Config should have a default profile."""
    cfg = Config.load()
    assert cfg.default_profile == "cmd"
    print("  PASS: Default profile")


def test_config_get_profile():
    """get_profile should return the correct profile or None."""
    cfg = Config.load()
    assert cfg.get_profile("cmd") is not None
    assert cfg.get_profile("cmd").command == "cmd.exe"
    assert cfg.get_profile("nonexistent") is None
    print("  PASS: get_profile")


def test_config_get_shell_command():
    """get_shell_command should return (command, args) for a profile."""
    cfg = Config.load()
    cmd, args = cfg.get_shell_command("powershell")
    assert cmd == "powershell.exe"
    assert args == ["-NoLogo", "-NoProfile"]

    # Fallback to cmd for unknown profile
    cmd, args = cfg.get_shell_command("nonexistent")
    assert cmd == "cmd.exe"
    assert args == []
    print("  PASS: get_shell_command")


def test_config_loads_keybindings():
    """Config should load keybindings from settings.toml."""
    cfg = Config.load()
    # settings.toml has: "Ctrl+Shift+N" = "profile_picker"
    #                    "Ctrl+Shift+F" = "find"
    kb_names = [kb.shortcut for kb in cfg.keybindings]
    assert "Ctrl+Shift+N" in kb_names
    assert "Ctrl+Shift+F" in kb_names
    print("  PASS: Config loads keybindings")


def test_config_ignores_invalid_actions():
    """Keybindings with unknown actions should be ignored."""
    import tempfile
    import toml
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        toml.dump({"keybindings": {"Ctrl+X": "nonexistent_action"}}, f)
        f.flush()
        path = f.name

    try:
        cfg = Config.load(path)
        assert len(cfg.keybindings) == 0
        print("  PASS: Invalid keybinding actions ignored")
    finally:
        os.unlink(path)


def test_builtin_actions_completeness():
    """BUILTIN_ACTIONS should contain all expected action names."""
    expected = {
        "new_tab", "close_tab", "next_tab", "prev_tab",
        "split_horizontal", "split_vertical",
        "font_bigger", "font_smaller", "font_reset",
        "theme_cycle", "theme_picker",
        "toggle_opacity", "copy", "paste",
        "find", "profile_picker", "ssh_connect",
        "serial_connect", "wsl_connect",
    }
    assert expected == BUILTIN_ACTIONS
    print("  PASS: BUILTIN_ACTIONS complete")


def test_keybinding_dataclass():
    """Keybinding should store shortcut and action."""
    kb = Keybinding(shortcut="Ctrl+T", action="new_tab")
    assert kb.shortcut == "Ctrl+T"
    assert kb.action == "new_tab"
    print("  PASS: Keybinding dataclass")


def test_search_bar_import():
    """SearchBar should be importable."""
    from search_bar import SearchBar
    assert SearchBar is not None
    print("  PASS: SearchBar importable")


def test_profile_picker_import():
    """ProfilePickerDialog should be importable."""
    from profile_picker import ProfilePickerDialog
    assert ProfilePickerDialog is not None
    print("  PASS: ProfilePickerDialog importable")


def run_all():
    print("Running profile/keybinding tests...")
    test_profile_dataclass()
    test_profile_with_overrides()
    test_config_loads_profiles()
    test_config_default_profile()
    test_config_get_profile()
    test_config_get_shell_command()
    test_config_loads_keybindings()
    test_config_ignores_invalid_actions()
    test_builtin_actions_completeness()
    test_keybinding_dataclass()
    test_search_bar_import()
    test_profile_picker_import()
    print("All profile/keybinding tests passed!\n")


if __name__ == "__main__":
    run_all()
