# Bug Fix Prompt for Google Jules

## Project
OmniTerm — A terminal emulator built with Python 3.13 + PyQt6. Uses ConPTY on Windows, pty on Linux/macOS.

**Repository**: https://github.com/BDib/OmniTerm  
**Branch**: master  
**Current version**: 2.5.3  

## Critical Bugs to Fix

### Bug 1: `-v` / `--version` flag produces no output

**Root cause**: Both PyInstaller (`console=False` in `OmniTerm.spec`) and Nuitka (`--windows-console-mode=disable`) build windowed executables with no console. The current implementation uses `print()` which goes to nowhere in a windowed app.

**Current code** (`src/Main.py`):
```python
parser.add_argument("--version", "-v", action="store_true",
                    help="Show version and exit")
# ...
if args.version:
    print(f"OmniTerm v{VERSION}")
    sys.exit(0)
```

**Fix needed**: When `--version` is passed, allocate a console window (via `AllocConsole` on Windows) so the version string is visible, OR use a `QMessageBox` to show the version. The AllocateConsole approach is better because it mimics standard CLI behavior.

Suggested approach:
```python
if args.version:
    if getattr(sys, 'frozen', False):
        # Allocated console for windowed builds
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.AllocConsole()
        import io
        sys.stdout = io.TextIOWrapper(k32.GetStdHandle(-11), encoding='utf-8')
        sys.stderr = io.TextIOWrapper(k32.GetStdHandle(-12), encoding='utf-8')
    print(f"OmniTerm v{VERSION}")
    sys.exit(0)
```

### Bug 2: Application crashes on exit (X button or typing `exit`)

**Symptoms**:
- Clicking the window X button hangs, then crashes
- Typing `exit` in the shell tab hangs, then crashes
- User must forcefully kill the process

**This was fixed in v2.5.1** but appears to have regressed.

**Key files**:
- `src/conpty.py` — `kill()` method (line 98), `_read_loop()` method (line 192)
- `src/terminal_ui.py` — `closeEvent()` (line 1336), `kill_all_engines()` (line 1361), `_close_tab()` (line 991)

**How the exit flow should work**:
1. Shell exits → `ConPTY._read_loop` detects EOF (ReadFile returns 0 bytes)
2. `_read_loop` sets `self._alive = False` and emits `self.exited`
3. `MainWindow._on_tab_process_exited` calls `_close_tab`
4. `_close_tab` closes the tab (or calls `self.close()` for last tab)
5. `closeEvent` calls `kill_all_engines()` which calls `engine.kill()`
6. `kill()` closes pipe handles to unblock any pending ReadFile

**What to investigate**:
- Check if `_read_loop` is stuck in `ReadFile` and never breaking
- Check if `kill()` is actually closing pipe handles correctly
- Check if there's a deadlock between the reader thread and the main thread
- Check if `deleteLater()` vs immediate deletion causes issues
- Check the `_closing` flag flow — is it preventing cleanup?

**Previous fix (v2.5.1)**:
- `kill()` closes pipe handles (`h_read`, `h_write`) after terminating the process
- Added `GetExitCodeProcess` safety net in `_read_loop`
- Removed `_closing` guard from `_on_tab_process_exited`
- Reordered `_close_tab` to call `deleteLater()` before `removeTab()`

**Possible regression causes**:
- The `from config import VERSION` import added to `terminal_ui.py` shouldn't cause issues
- The window title change shouldn't cause issues
- The Help menu addition shouldn't cause issues
- Check if there's a threading deadlock in the cleanup path

## Build System

- **Nuitka** (default): `.\build.ps1` — uses `--onefile --windows-console-mode=disable`
- **PyInstaller** (fallback): `.\build.ps1 pyinstaller` — uses `console=False` in `OmniTerm.spec`
- **Installer**: `.\build.ps1 installer` — Inno Setup

Both builds produce windowed executables with no console.

## Testing

```bash
python -m pytest tests/ -v    # 145 tests, all should pass
```

## Version

The version is defined in `src/config.py`:
```python
VERSION = "2.5.3"
```

## Constraints

- Must work with both PyInstaller and Nuitka builds
- Must work on Windows 10+ (ConPTY requires build 17763+)
- Python 3.11, 3.12, 3.13
- 145 existing tests must continue to pass
