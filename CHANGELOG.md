# Changelog

## v2.5.4 (2026-07-23)
- **Fix**: Windows CLI `--version` output with robust handle translation
- **Fix**: Tab close / engine exits are now thread-safe via Qt signals and widget mapping
- Removed unused local variables and dead code

## v2.5.3 (2026-07-23)
- Removed issue markdown files (tracked as GitHub Issues #3-#6)
- Version bump to 2.5.3

## v2.5.2 (2026-07-23)
- Added exit fix integration tests (test_exit_fix.py)
- All 145 tests passing

## v2.5.1 (2026-07-23)
- **Fix**: `exit` command not closing tab — `kill()` now closes pipe handles to unblock `ReadFile`
- Added `GetExitCodeProcess` safety net in `_read_loop`

## v2.5.0 (2026-07-23)
- **Fix**: Close/X button unreliable — removed `_closing` guard from `_on_tab_process_exited`
- **Fix**: Search methods crash — `_search_next`/`_search_prev` now use parent MainWindow's tab widget
- Reordered `_close_tab` to call `deleteLater()` before `removeTab()`

## v2.4.4 (2026-07-22)
- **Fix**: Exit command not closing tab — break on both `not ok` and `read.value == 0`

## v2.4.3 (2026-07-22)
- **Fix**: Exit/close crash — added `GetExitCodeProcess` check, removed premature pipe close

## v2.4.2 (2026-07-22)
- **Fix**: RTL toggle crash — removed reference to non-existent `_input` attribute
- **Fix**: Exit not closing tab — `kill()` closes read pipe handle

## v2.4.1 (2026-07-22)
- **Fix**: RTL alignment — `document().setDefaultTextDirection()` for visual text movement
- Added `faulthandler` for crash diagnosis, signal handlers for SIGTERM/SIGINT

## v2.4.0 (2026-07-22)
- Save/Export output as HTML (Ctrl+Shift+H) or Text (Ctrl+Shift+S)
- RTL alignment fix, shutdown safety (`_closing` flag, `_killed` guard)
- CI: Added Windows ARM64 and Linux ARM64 builds

## v2.3.0 (2026-07-22)
- CI/CD: Full cross-platform builds (6 platforms: Windows/Linux/macOS x64+ARM64)

## v2.2.0 (2026-07-22)
- **Major**: Unified TerminalScreen widget (single-pane architecture)
- Arabic shaping + bidirectional text, cross-platform PTY (ConPTY + pty)
- Dynamic i18n (English/Arabic), CWD path resolution

## v2.1.0–v2.1.6 (2026-07-22)
- ConPTY backend fixes: STARTUPINFOEXW struct, COORD dimensions, PROCESS_INFORMATION, writable buffer, two-pipe architecture, direct write path, arrow key handling
- Removed winpty dependency

## v2.0.0 (2026-07-21)
- **Major**: ConPTY backend replaces winpty — native Windows Pseudo Console API
- Source optimization, comprehensive test suite (141 tests)

## v1.0.0–v1.6.0 (2026-07-20–21)
- Initial release through config fallback, search dialog, input fixes
- Profile management, 13 themes, Nuitka build, Inno Setup installer
