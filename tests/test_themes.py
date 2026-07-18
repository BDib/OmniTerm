"""
Unit tests for OmniTerm themes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from themes import get_theme, list_themes, CAMPBELL, SOLARIZED_DARK, ONE_HALF_DARK, Theme


def test_list_themes():
    """Should return at least 3 themes sorted alphabetically."""
    themes = list_themes()
    assert len(themes) >= 3
    assert themes == sorted(themes)
    assert "campbell" in themes
    assert "solarized_dark" in themes
    assert "one_half_dark" in themes
    print(f"  PASS: {len(themes)} themes listed: {themes}")


def test_get_theme_campbell():
    """Getting 'campbell' should return the CAMPBELL theme."""
    t = get_theme("campbell")
    assert t is CAMPBELL
    assert t.name == "Campbell"
    assert t.background == "#0C0C0C"
    assert t.foreground == "#CCCCCC"
    print("  PASS: get_theme('campbell') returns CAMPBELL")


def test_get_theme_case_insensitive():
    """Theme lookup should be case-insensitive."""
    assert get_theme("CAMPBELL") is CAMPBELL
    assert get_theme("Campbell") is CAMPBELL
    assert get_theme("SOLARIZED_DARK") is SOLARIZED_DARK
    print("  PASS: Case-insensitive lookup works")


def test_get_theme_fallback():
    """Unknown theme name should fall back to Campbell."""
    t = get_theme("nonexistent_theme_xyz")
    assert t is CAMPBELL
    print("  PASS: Unknown theme falls back to Campbell")


def test_theme_has_ansi_colors():
    """Each theme should have 16 ANSI colors."""
    for name in list_themes():
        t = get_theme(name)
        assert len(t.ansi) == 16, f"Theme {name} has {len(t.ansi)} colors, expected 16"
        for key in (
            "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
            "bright_black", "bright_red", "bright_green", "bright_yellow",
            "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
        ):
            assert key in t.ansi, f"Theme {name} missing ANSI key: {key}"
            assert t.ansi[key].startswith("#"), f"Theme {name} color {key} not hex: {t.ansi[key]}"
    print("  PASS: All themes have 16 valid ANSI colors")


def test_theme_stylesheet():
    """Theme.stylesheet() should produce valid CSS-like output."""
    t = CAMPBELL
    css = t.stylesheet("Consolas", 12)
    assert "Consolas" in css
    assert "12px" in css
    assert t.background in css
    assert t.foreground in css
    assert "selection-background-color" in css
    print("  PASS: Theme.stylesheet() produces valid output")


def test_all_themes_stylesheet():
    """Every theme should produce a stylesheet without errors."""
    for name in list_themes():
        t = get_theme(name)
        css = t.stylesheet("Courier New", 10)
        assert isinstance(css, str)
        assert len(css) > 50
    print("  PASS: All themes produce valid stylesheets")


def test_theme_dataclass_fields():
    """Theme dataclass should have required fields."""
    t = CAMPBELL
    assert hasattr(t, "name")
    assert hasattr(t, "background")
    assert hasattr(t, "foreground")
    assert hasattr(t, "cursor")
    assert hasattr(t, "selection_bg")
    assert hasattr(t, "selection_fg")
    assert hasattr(t, "ansi")
    print("  PASS: Theme dataclass has all required fields")


def run_all():
    print("Running theme tests...")
    test_list_themes()
    test_get_theme_campbell()
    test_get_theme_case_insensitive()
    test_get_theme_fallback()
    test_theme_has_ansi_colors()
    test_theme_stylesheet()
    test_all_themes_stylesheet()
    test_theme_dataclass_fields()
    print("All theme tests passed!\n")


if __name__ == "__main__":
    run_all()
