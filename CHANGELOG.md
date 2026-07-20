# Changelog

## v1.1.0 — Session 2 (2026-07-20)

### Architecture
- **Rewrote TerminalWidget** from a single `QTextEdit` to a `QWidget` with separate `QTextEdit` (output) + `QLineEdit` (input)
  - Output area: read-only QTextEdit renders shell output with ANSI colors
  - Input area: QLineEdit provides native cursor, editing, and history
  - Solved fundamental QTextEdit limitations (hidden cursor when read-only, inability to overwrite text, internal key handling fighting overrides)

### Input Handling
- **Command history**: Up/Down arrows in the input field cycle through previously entered commands
- **Native editing**: Left/Right arrows, Home/End, Delete, Backspace all work via QLineEdit's built-in handling
- **Enter**: sends command + `\r` to the shell; shell echoes output back to the output area

### Output Rendering
- **ANSI parser**: Handles SGR (colors, bold, italic, underline), cursor movement, erase sequences
- **ANSI renderer**: Maps parsed spans to `QTextCharFormat` for styled output
- **ERASE_DISPLAY** (`cls`/`clear`/`Clear-Host`): Now properly clears the output widget
- **ERASE_LINE** (`\x1b[K`): Clears from cursor to end of line
- **Carriage return**: Ignored for `\r\n` line endings (avoids blank lines and text duplication)
- **CURSOR_POS handling**: Handles PSReadLine rewrites — when cursor moves backward within a line, old text is deleted before inserting new text (fixes doubled characters in PowerShell)
- **CURSOR_BACK / CURSOR_FORWARD**: Handled for cursor movement sequences

### Key Fixes
- **Delete key**: Now handled natively by QLineEdit (no longer inserts tab/space)
- **Left/Right arrows**: Work natively in QLineEdit
- **Backspace**: Sends `\x7f` (DEL) instead of `\b` (BS) — what most shells expect
- **`cls`/`clear`**: ERASE_DISPLAY span now clears the output widget
- **`exit` command**: Closes the tab; last tab closes the application
- **`pause` support**: All keystrokes forwarded to shell via QLineEdit → Enter flow
- **Doubled text**: Eliminated by using QLineEdit instead of forwarding keystrokes to shell
- **PowerShell doubled text**: Fixed by adding `-NoProfile` to disable PSReadLine, and by handling CURSOR_POS for line rewrites

### Project Structure
- Moved all Python source files to `src/` directory
- Added `src/__init__.py`
- Updated all imports, test paths, build scripts, spec file, and CI workflow
- `settings.toml` remains at project root (config.py looks one directory up)

### Tests
- **11 test suites, 100+ tests** all passing
- Added `test_keyboard.py`: 21 tests for input handling (QLineEdit-based)
- Added `test_rendering.py`: 7 tests for ANSI rendering pipeline
- Updated `test_distribution.py` for new `src/Main.py` entry point
- Updated `tests/run_all.py` to include new test modules

### Build
- Updated `OmniTerm.spec` entry point to `src/Main.py`
- Updated `build.bat` and `build.ps1` to find `config.VERSION` via `src/`
- Updated CI workflow lint path from `*.py` to `src/`

---

## v1.0.0 — Session 1 (2026-07-20)

### Initial features
- Multi-tab terminal with PTY (winpty), SSH, and serial support
- ANSI color rendering (256-color, RGB, bold, italic, underline)
- Mouse protocol support (xterm)
- Theme system (Campbell, Solarized Dark, One Half Dark)
- Configurable via `settings.toml`
- Profile picker (cmd, PowerShell, pwsh, WSL, Git Bash)
- Split panes (horizontal/vertical)
- Search bar
- Font size controls, opacity toggle
