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
1. **`_on_tab_process_exited` returned early when `_closing` was True** — When the user clicks X to close the window, `closeEvent` sets `_closing = True` and calls `kill_all_engines()`. This triggers `ConPTYEngine.kill()` → `TerminateProcess` → `_read_loop` breaks → `exited` signal fires → `_on_tab_process_exited` is called — but it returned immediately because `_closing` was already True, so the tab was never cleaned up before the window closed.
2. **`deleteLater()` after `removeTab()`** — The widget was removed from tabs before it was deleted, which could cause signal delivery issues.
3. **Search methods referenced `self._tabs`** — `_search_next` and `_search_prev` in `TerminalWidget` referenced `self._tabs` which doesn't exist on `TerminalWidget` (it's on `MainWindow`).

## Fix (v2.5.0)

1. Removed the `_closing` check from `_on_tab_process_exited` — the method now always attempts to close the tab if it exists, regardless of the `_closing` state.
2. Reordered `_close_tab` to call `deleteLater()` before `removeTab()` to prevent signal delivery issues.
3. Fixed `_search_next` and `_search_prev` in `TerminalWidget` to access the parent `MainWindow`'s tab widget correctly.

## Files Changed

- `src/terminal_ui.py` — `_on_tab_process_exited()`, `_close_tab()`, `_search_next()`, `_search_prev()`

## Testing

- All 142 tests pass
- Verified: exit command closes tab, last tab exit closes window, X button and Alt+F4 work reliably

## Environment

- Windows 11, Python 3.13
- Built with PyInstaller (also affects Nuitka and Python interpreter runs)
- v2.5.0
