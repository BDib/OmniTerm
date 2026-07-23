import sys
import os
import traceback
import faulthandler
import signal
import argparse
from pathlib import Path

# Add src/ to path so sibling modules are importable
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from PyQt6.QtWidgets import QApplication  # noqa: E402
from config import Config, VERSION  # noqa: E402
from terminal_ui import MainWindow  # noqa: E402

# ── Error logging — only created on crash or --verbose ──────────────
if getattr(sys, "frozen", False):
    _app_dir = os.getcwd()
else:
    _app_dir = os.getcwd()
_log_path = os.path.join(_app_dir, "errors.txt")

# Enable faulthandler to dump traceback on segfault/SIGFPE/etc.
try:
    _fault_log = open(_log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_fault_log)
except Exception:
    faulthandler.enable()


def _write_log(msg: str):
    """Append a message to errors.txt."""
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{__import__('time').strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _excepthook(exc_type, exc_value, exc_tb):
    """Log unhandled exceptions to errors.txt."""
    try:
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write("\n=== Unhandled exception ===\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
            f.write("\n")
    except Exception:
        pass

sys.excepthook = _excepthook


def _signal_handler(signum, frame):
    """Log when killed by signal."""
    _write_log(f"Received signal {signum}, exiting...")
    sys.exit(128 + signum)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def parse_args():
    parser = argparse.ArgumentParser(
        description="OmniTerm — Windows Terminal Emulator",
        epilog=f"OmniTerm v{VERSION} — MIT License",
    )
    parser.add_argument("--config", "-c", default=None,
                        help="Path to settings.toml")
    parser.add_argument("--shell", "-s", default=None,
                        help="Shell command to run (e.g., powershell.exe)")
    parser.add_argument("--plain", action="store_true",
                        help="Disable ANSI color rendering")
    parser.add_argument("--profile", "-p", default=None,
                        help="Open with a named profile from settings.toml")
    parser.add_argument("--verbose", action="store_true",
                        help="Log startup details to errors.txt")
    parser.add_argument("--version", "-v", action="store_true",
                        help="Show version and exit")
    parser.add_argument("path", nargs="?", default=None,
                        help="Optional initial working directory path to start OmniTerm in")
    return parser.parse_args()


def run():
    args = parse_args()

    if args.version:
        if getattr(sys, "frozen", False) and os.name == "nt":
            import ctypes
            import msvcrt
            # Try to attach to the parent console (e.g. cmd.exe, powershell.exe)
            attached = ctypes.windll.kernel32.AttachConsole(-1)
            if not attached:
                # If not run from an existing console, allocate a new one
                ctypes.windll.kernel32.AllocConsole()
            # Redirect standard streams using robust OS file handle translation
            stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
            stderr_handle = ctypes.windll.kernel32.GetStdHandle(-12)
            if stdout_handle:
                fd_out = msvcrt.open_osfhandle(stdout_handle, os.O_WRONLY)
                sys.stdout = open(fd_out, "w", encoding="utf-8", closefd=False)
            if stderr_handle:
                fd_err = msvcrt.open_osfhandle(stderr_handle, os.O_WRONLY)
                sys.stderr = open(fd_err, "w", encoding="utf-8", closefd=False)
        # Print version (will be visible on attached/allocated console or standard terminal)
        print(f"OmniTerm v{VERSION}")
        if sys.stdout:
            sys.stdout.flush()
        sys.exit(0)

    if args.verbose:
        _write_log(f"OmniTerm v{VERSION} starting")
        _write_log(f"  Python: {sys.version}")
        _write_log(f"  Executable: {sys.executable}")
        _write_log(f"  CWD: {os.getcwd()}")
        _write_log(f"  Frozen: {getattr(sys, 'frozen', False)}")

    try:
        cfg = Config.load(args.config)
        if args.verbose:
            _write_log(f"Config loaded: {len(cfg.profiles)} profiles, "
                       f"default={cfg.default_profile}")
            for name, p in cfg.profiles.items():
                _write_log(f"  Profile {name}: {p.command} "
                           f"{'[admin]' if p.admin else ''}")

        app = QApplication(sys.argv)

        shell_cmd = None
        if args.profile:
            profile = cfg.get_profile(args.profile)
            if profile:
                shell_cmd = profile.command
                if args.verbose:
                    _write_log(f"Profile '{args.profile}' -> {shell_cmd}")
            else:
                _write_log(f"Profile '{args.profile}' not found, using default")
        elif args.shell:
            shell_cmd = args.shell
            if args.verbose:
                _write_log(f"Shell: {shell_cmd}")

        # Resolve initial working directory (CWD)
        target_dir = None
        if args.path:
            resolved = os.path.abspath(args.path)
            if os.path.isdir(resolved):
                target_dir = resolved
        else:
            if getattr(sys, "frozen", False):
                install_dir = os.path.dirname(sys.executable)
            else:
                # development: project root contains src/
                install_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            cwd = os.path.abspath(os.getcwd())
            inst = os.path.abspath(install_dir)
            if cwd == inst:
                # Started from install dir -> default to home folder
                target_dir = os.path.expanduser("~")
            else:
                # Started from elsewhere (like CLI command) -> keep current working directory
                target_dir = cwd

        if args.verbose:
            _write_log(f"Creating MainWindow with CWD: {target_dir} ...")

        window = MainWindow(cfg, plain_mode=args.plain, shell=shell_cmd, cwd=target_dir)

        if args.verbose:
            _write_log("MainWindow created, showing...")

        window.show()

        if args.verbose:
            _write_log("Event loop starting")

        status = app.exec()
        window.kill_all_engines()

        if args.verbose:
            _write_log(f"Event loop ended, status={status}")

        sys.exit(status)

    except Exception as exc:
        _write_log(f"FATAL: {exc}")
        _write_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    run()
