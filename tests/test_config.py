"""
Unit tests for OmniTerm configuration loading.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add parent dir to path so we can import modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import Config, UIConfig, UIBehavior, VERSION


def test_version_exists():
    """VERSION should be a non-empty string."""
    assert isinstance(VERSION, str)
    assert len(VERSION) > 0
    print(f"  PASS: VERSION = {VERSION}")


def test_default_config():
    """Loading with no file should return sensible defaults."""
    cfg = Config.load(Path("/nonexistent/path/settings.toml"))
    assert cfg.ui.opacity == 0.98
    assert cfg.ui.font_family == "Cascadia Code"
    assert cfg.ui.font_size == 14
    assert cfg.ui.theme == "campbell"
    assert cfg.ui.cursor_style == "bar"
    assert cfg.ui.cursor_blink is True
    assert cfg.behavior.rtl_threshold == 0.7
    print("  PASS: Default config values correct")


def test_load_from_file():
    """Loading from a valid TOML file should override defaults."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write('[ui]\nfont_size = 20\ntheme = "solarized_dark"\n')
        f.flush()
        path = f.name

    try:
        cfg = Config.load(path)
        assert cfg.ui.font_size == 20
        assert cfg.ui.theme == "solarized_dark"
        # Defaults should still be there for unspecified keys
        assert cfg.ui.font_family == "Cascadia Code"
        assert cfg.ui.opacity == 0.98
        print("  PASS: File override works")
    finally:
        os.unlink(path)


def test_partial_override():
    """Only overridden keys should change; rest stay at defaults."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write('[ui]\nopacity = 0.5\n')
        f.flush()
        path = f.name

    try:
        cfg = Config.load(path)
        assert cfg.ui.opacity == 0.5
        assert cfg.ui.font_size == 14  # default
        assert cfg.ui.theme == "campbell"  # default
        print("  PASS: Partial override preserves defaults")
    finally:
        os.unlink(path)


def test_malformed_toml():
    """Malformed TOML should fall back to defaults, not crash."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write("this is not valid toml {{{{")
        f.flush()
        path = f.name

    try:
        cfg = Config.load(path)
        assert cfg.ui.font_size == 14  # default
        print("  PASS: Malformed TOML falls back to defaults")
    finally:
        os.unlink(path)


def test_behavior_section():
    """Behavior section should load correctly."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    ) as f:
        f.write("[behavior]\nrtl_threshold = 0.5\n")
        f.flush()
        path = f.name

    try:
        cfg = Config.load(path)
        assert cfg.behavior.rtl_threshold == 0.5
        print("  PASS: Behavior section loads correctly")
    finally:
        os.unlink(path)


def run_all():
    print("Running config tests...")
    test_version_exists()
    test_default_config()
    test_load_from_file()
    test_partial_override()
    test_malformed_toml()
    test_behavior_section()
    print("All config tests passed!\n")


if __name__ == "__main__":
    run_all()
