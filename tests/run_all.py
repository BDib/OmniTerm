"""
OmniTerm test runner.

Runs all unit tests in the tests/ directory.
Usage:  python tests/run_all.py
"""

import sys
from pathlib import Path

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import (
    test_config, test_themes, test_ansi_parser,
    test_mouse_scroll, test_tabs, test_profiles, test_distribution,
    test_ssh, test_serial_wsl,
)


def main():
    passed = 0
    failed = 0

    for module in (test_config, test_themes, test_ansi_parser, test_mouse_scroll, test_tabs, test_profiles, test_distribution, test_ssh, test_serial_wsl):
        try:
            module.run_all()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {module.__name__}: {e}")
            failed += 1

    print("=" * 50)
    if failed == 0:
        print(f"All test suites passed ({passed} suites)")
    else:
        print(f"{passed} passed, {failed} failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
