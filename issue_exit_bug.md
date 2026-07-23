## Description

Typing `exit` in a shell tab does not close the tab. Closing the last tab should close the application, but it doesn't. The window close button (X) and Alt+F4 also don't work reliably — the application hangs or crashes silently.

## Expected Behavior

1. Typing `exit` in a tab should close that tab
2. Typing `exit` in the last remaining tab should close the application
3. Clicking the X button or Alt+F4 should close the application cleanly

## Root Cause Analysis

The signal chain should work as follows:
1. Shell exits → `ConPTY._read_loop` detects EOF (ReadFile returns 0 bytes)
2. `_read_loop` sets `self._alive = False` and emits `self.exited`
3. `TerminalEngine._on_conpty_exit` re-emits `self.signals.exited`
4. `MainWindow._on_tab_process_exited` calls `_close_tab`
5. `_close_tab` closes the tab (or calls `self.close()` for last tab)

The bugs were:
1. **`kill()` did not close pipe handles** — When the user types `exit`, the shell terminates but `ReadFile` blocks forever on the still-open pipe. The `exited` signal never fires, so the tab never closes.
2. **`_on_tab_process_exited` returned early when `_closing` was True** — When closing the window, `closeEvent` set `_closing = True` and called `kill_all_engines()`. The exit signal would fire but `_on_tab_process_exited` returned early.
3. **`deleteLater()` after `removeTab()`** — The widget was removed from tabs before it was deleted, causing signal delivery issues.
4. **Search methods referenced `self._tabs`** — `_search_next` and `_search_prev` in `TerminalWidget` referenced `self._tabs` which doesn't exist on `TerminalWidget`.

## Fix (v2.5.1)

1. `kill()` now closes pipe handles (`h_read`, `h_write`) after terminating the process. This unblocks `ReadFile` which catches the broken-pipe error and exits cleanly.
2. Added `GetExitCodeProcess` check in `_read_loop` as a safety net to detect process termination even if pipe reads stall.
3. Removed the `_closing` check from `_on_tab_process_exited`.
4. Reordered `_close_tab` to call `deleteLater()` before `removeTab()`.
5. Fixed `_search_next` and `_search_prev` in `TerminalWidget` to access the parent `MainWindow`'s tab widget correctly.

## Files Changed

- `src/conpty.py` — `kill()`, `_read_loop()`
- `src/terminal_ui.py` — `_on_tab_process_exited()`, `_close_tab()`, `_search_next()`, `_search_prev()`
- `src/config.py` — Version bump to 2.5.1

## Testing

- All 142 tests pass
- Nuitka build: 32.2 MB (working)
- PyInstaller build: 48.8 MB (working)
- Verified: exit command closes tab, last tab exit closes window, X button and Alt+F4 work reliably

## Environment

- Windows 11, Python 3.13
- Built with Nuitka and PyInstaller
- v2.5.1
