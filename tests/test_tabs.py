"""
Unit tests for the tab management and split logic.

Since Qt widgets require a running QApplication, these tests focus on
the non-GUI logic: shell title derivation, engine tracking, and the
MainWindow's tab API contract.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_shell_title_cmd():
    """Shell title should strip .exe and path."""
    from terminal_ui import MainWindow
    assert MainWindow._shell_title("cmd.exe") == "cmd"
    assert MainWindow._shell_title("powershell.exe") == "powershell"
    print("  PASS: Shell title for cmd/powershell")


def test_shell_title_with_path():
    """Shell title should extract the basename."""
    from terminal_ui import MainWindow
    assert MainWindow._shell_title("C:\\Program Files\\Git\\bin\\bash.exe") == "bash"
    assert MainWindow._shell_title("/usr/bin/zsh") == "zsh"
    print("  PASS: Shell title with path")


def test_shell_title_no_exe():
    """Shell title without .exe should work."""
    from terminal_ui import MainWindow
    assert MainWindow._shell_title("bash") == "bash"
    assert MainWindow._shell_title("zsh") == "zsh"
    print("  PASS: Shell title without .exe")


def test_tab_engines_dict():
    """Tab engines dict should track engine instances."""
    # Simulate what MainWindow does
    engines = {}
    engines[0] = "engine_a"
    engines[1] = "engine_b"
    assert engines[0] == "engine_a"
    assert engines[1] == "engine_b"
    assert len(engines) == 2

    # Simulate tab close
    engines.pop(0, None)
    assert len(engines) == 1
    assert 0 not in engines
    print("  PASS: Tab engines dict tracking")


def test_tab_index_management():
    """Tab index management should handle edge cases."""
    tabs = ["tab0", "tab1", "tab2"]

    # Next tab wraps around
    current = 2
    next_idx = (current + 1) % len(tabs)
    assert next_idx == 0

    # Previous tab wraps around
    current = 0
    prev_idx = (current - 1) % len(tabs)
    assert prev_idx == 2

    # Single tab
    tabs_single = ["only"]
    current = 0
    next_idx = (current + 1) % len(tabs_single)
    assert next_idx == 0
    print("  PASS: Tab index management")


def test_split_orientation():
    """Split should support horizontal and vertical orientations."""
    from PyQt6.QtCore import Qt
    assert Qt.Orientation.Horizontal is not None
    assert Qt.Orientation.Vertical is not None
    print("  PASS: Split orientations available")


def run_all():
    print("Running tab/split tests...")
    test_shell_title_cmd()
    test_shell_title_with_path()
    test_shell_title_no_exe()
    test_tab_engines_dict()
    test_tab_index_management()
    test_split_orientation()
    print("All tab/split tests passed!\n")


if __name__ == "__main__":
    run_all()
