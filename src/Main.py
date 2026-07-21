import sys
import os
import faulthandler
import traceback
import argparse
from pathlib import Path

# Add src/ to path so sibling modules are importable
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from PyQt6.QtWidgets import QApplication  # noqa: E402
from config import Config, VERSION  # noqa: E402
from terminal_ui import MainWindow  # noqa: E402

# Enable fault handler to log segfaults — write next to the exe
if getattr(sys, "frozen", False):
    _app_dir = os.path.dirname(sys.executable)
else:
    _app_dir = os.getcwd()
_log_path = os.path.join(_app_dir, "errors.txt")
faulthandler.enable(file=open(_log_path, "w"))

# Catch all unhandled exceptions
def _excepthook(exc_type, exc_value, exc_tb):
    with open(_log_path, "a") as f:
        f.write("=== Unhandled exception ===\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        f.write("\n")

sys.excepthook = _excepthook


def parse_args():
    parser = argparse.ArgumentParser(
        description="OmniTerm — Windows Terminal Emulator",
        epilog=f"OmniTerm v{VERSION} — MIT License",
    )
    parser.add_argument("--config", "-c", default=None,
                        help="Path to settings.toml")
    parser.add_argument("--shell", "-s", default=None,
                        help="Shell command to run (e.g., powershell.exe, wsl.exe)")
    parser.add_argument("--plain", action="store_true",
                        help="Disable ANSI color rendering (strip all escapes)")
    parser.add_argument("--profile", "-p", default=None,
                        help="Open with a named profile from settings.toml")
    parser.add_argument("--version", "-V", action="version",
                        version=f"OmniTerm v{VERSION}")
    return parser.parse_args()


def run():
    args = parse_args()
    cfg = Config.load(args.config)

    app = QApplication(sys.argv)

    # Determine initial shell
    shell_cmd = None
    if args.profile:
        profile = cfg.get_profile(args.profile)
        if profile:
            shell_cmd = profile.command
        else:
            print(f"Warning: profile '{args.profile}' not found, using default", file=sys.stderr)
    elif args.shell:
        shell_cmd = args.shell

    window = MainWindow(cfg, plain_mode=args.plain, shell=shell_cmd)

    window.show()

    status = app.exec()
    window.kill_all_engines()
    sys.exit(status)


if __name__ == "__main__":
    run()
