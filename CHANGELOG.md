# Changelog

## v2.1.5 — Session 9 (2026-07-22)

### Fix: Echo feedback loop creating junk files
- **Root cause** — ConPTY used a single pipe for both input and output. The host read its own input back from the pipe, which was fed into the shell as commands. Shell output fragments became filenames.
- **Fix** — Use TWO separate pipes: one for input (host → shell), one for output (shell → host). This isolates the data flow and eliminates the echo loop.
- Verified working in Python, Nuitka, and PyInstaller builds — no junk files created.

---

## v2.1.4 — Session 9 (2026-07-22)

### Fix: Input not reaching ConPTY shell
- **Root cause** — `TerminalEngine.write()` put data into `input_queue`, but ConPTY has no writer thread consuming that queue. Data was silently dropped.
- **Fix** — When using ConPTY, `write()` now calls `self._conpty.write()` directly instead of using the queue.

---

## v2.1.3 — Session 9 (2026-07-22)

### Fix: Missing PROCESS_INFORMATION struct
- **Root cause** — `ctypes.wintypes` does not have `PROCESS_INFORMATION`. The ConPTY engine used `wt.PROCESS_INFORMATION()` which threw `AttributeError`.
- **Fix** — Defined `PROCESS_INFORMATION` as a ctypes Structure with `hProcess`, `hThread`, `dwProcessId`, `dwThreadId` fields.
- Verified working in Python interpreter, Nuitka, and PyInstaller builds.

---

## v2.1.2 — Session 9 (2026-07-22)

### Fix: CreatePseudoConsole E_INVALIDARG
- **Root cause** — `CreatePseudoConsole` was called with `COORD(0, 0)` as the console size. A zero-size console is invalid and returns `E_INVALIDARG` (0x80070057).
- **Fix** — Pass the actual requested dimensions `(w, h)` to `CreatePseudoConsole` instead of `(0, 0)`. Removed redundant `ResizePseudoConsole` call.
- This fix applies to all run modes: Python interpreter, PyInstaller, and Nuitka.

---

## v2.1.1 — Session 9 (2026-07-22)

### Fix: ConPTY shell not launching
- **Root cause** — `CreateProcessW` requires a writable buffer for `lpCommandLine`, but a Python string was being passed directly. ctypes conversion was insufficient on Nuitka onefile builds.
- **Fix** — Use `ctypes.create_unicode_buffer(cmd)` to create a proper writable buffer.
- **Added error logging** — ConPTY now logs each API call result to errors.txt for debugging.
- **CI fixes** — Drop Python 3.10, set fail-fast:false, add conftest.py for Qt cleanup, tag-only triggers.

---

## v2.1.0 — Session 8 (2026-07-22)

### Critical Fix: Nuitka 5-second crash
- **Root cause** — ConPTY used `STARTUPINFOW` (basic struct) instead of `STARTUPINFOEXW`. Python's ctypes allows setting `lpAttributeList` as a Python attribute, but it was never written to the binary memory `CreateProcessW` reads. The pseudo console attribute was silently ignored, leaving the child process without a console.
- **Fix** — Defined proper `STARTUPINFOEXW` ctypes Structure with `lpAttributeList` in the binary layout. `cb` now reflects the correct extended struct size.
- **Removed `CREATE_NO_WINDOW`** — ConPTY owns its own console; this flag was conflicting.
- **Fixed write path** — Changed from `WriteConsoleInputCharacterW` (console input buffer) to `WriteFile` (pipe) for correct ConPTY input.
- **Improved read loop** — Breaks cleanly on pipe close instead of spinning.
- **Proper cleanup** — Pipe handles closed in `kill()` to prevent handle leaks.

### Cleanup
- Removed dead winpty fallback from `terminal_core.py` (not in requirements)
- Added comprehensive error logging throughout ConPTY lifecycle
- All 141 tests passing

### Documentation
- Full README rewrite — accurate architecture, build instructions, test commands
- BUILD.md updated with troubleshooting section
- CONTRIBUTING.md updated with pytest commands and project structure
- requirements.txt updated with minimum version pins

---

## v2.0.0 — Session 7 (2026-07-21)

### ConPTY Backend (major)
- **ConPTY replaces winpty** — uses Windows' native Pseudo Console API via ctypes
- **Automatic fallback** — tries ConPTY first, falls back to winpty if unavailable
- **No more winpty dependency** — removed from requirements.txt
- **Fixed cmd.exe crash** — winpty pipe connectivity issue caused 5-second exit; ConPTY resolves this
- **Admin mode** — elevated processes launch via ShellExecuteW

### Source Optimization
- Removed redundant code, blank lines, excessive comments
- One-liner patterns where appropriate
- Streamlined error handling across all modules

### Tests
- Comprehensive keyboard input tests (all keys, Ctrl combinations, navigation)
- Rendering pipeline tests (CR, ERASE_DISPLAY, ERASE_LINE, ANSI colors)
- Profile management tests (add, edit, delete, admin flag)
- Search dialog tests (find next/prev, highlight all)
- Config tests (defaults, auto-creation, path resolution)

### Documentation
- CHANGELOG.md updated for v2.0.0
- Roadmap.md updated
- FIXES.md renamed to TECHNICAL_NOTES.md (in .gitignore)
- KNOWN_ISSUES.md, CONTRIBUTING.md, BUILD.md maintained

### Build
- Nuitka onefile: ~26 MB (fast startup)
- PyInstaller: ~44 MB (fallback)
- Inno Setup installer
- All three verified working

---

## v1.6.0 — Session 6 (2026-07-21)

### Config & Startup
- **settings.toml auto-creation** — If settings.toml is missing, it's created with sensible defaults on first run
- **Config fallback** — All settings have sensible defaults; missing config gracefully falls back
- **errors.txt** — Only created on crash (no longer created at startup)

### Search
- **SearchDialog** — Converted from broken floating widget to proper QDialog popup
- **F3/Shift+F3** — Next/previous match navigation
- **All instances highlighted** — Blue highlights on all matches, counter shows position

### Input & Navigation
- **Input area**: QTextEdit handles text entry natively (characters appear there)
- **Navigation keys**: Arrows, Home/End forwarded to shell for cursor movement
- **Up/Down**: Forwarded to shell for command history
- **Output area**: Read-only, normal navigation when focused

### Menu & Edit
- **Cut**: Only works in input area (output is read-only)
- **Copy**: Works in both output and input
- **Find**: Opens proper search dialog (F3 / Ctrl+F)

---

## v1.5.0 — Session 5 (2026-07-21)

### Search / Find
- **F3** opens search bar or finds next match
- **Shift+F3** finds previous match
- Search bar now lives inside each TerminalWidget (positioned at bottom of output)
- All matches highlighted with blue background
- Match counter shows current/total (e.g., "3/15")
- Enter in search field finds next, Escape or close button hides bar

### Documentation
- **KNOWN_ISSUES.md** — Known limitations and platform issues
- **CONTRIBUTING.md** — How to contribute, project structure, building
- **BUILD.md** — Detailed build instructions (Nuitka, PyInstaller, installer)
- Updated CHANGELOG.md, Roadmap.md, README.md

### Menu Cleanup
- Removed duplicate shortcuts between TerminalWidget and MainWindow
- All menu items verified working: File, Edit, View, Tools, Window

---

## v1.4.0 — Session 5 (2026-07-21)

### Build & Distribution
- **Nuitka on CI** — GitHub Actions now builds with Nuitka (faster startup)
- **Win10/11 x64 naming** — All release files include platform tag: `OmniTerm-win10-x64.exe`, `pyOmniTerm-win10-x64.exe`, `OmniTermSetup-win10-x64.exe`
- **Release notes** — Auto-generated with file descriptions and requirements
- **CI fixes** — Fixed YAML syntax, PyInstaller spec dynamic winpty detection, test runner QApplication singleton

### Fixes
- **PyInstaller spec** — Dynamic winpty DLL detection works across Python 3.10–3.13
- **Test runner** — QApplication created once to prevent hangs on CI
- **Distribution test** — Updated for new CI command format
- **CI lint** — Made ruff non-blocking to avoid version mismatches

---

## v1.3.0 — Session 4 (2026-07-20)

### Build System
- **Nuitka as default** — 7.5x faster startup (13ms vs 97ms), 2.3x smaller (18.9 MB vs 43.8 MB)
- **PyInstaller retained** as fallback via `.\build.ps1 pyinstaller`
- **Inno Setup installer** — Professional Windows installer with Start Menu, desktop shortcut, file associations
- **Build modes**: `release` (Nuitka default), `pyinstaller`, `debug`, `installer`, `clean`

### Installer
- `installer/omniterm.iss` — Inno Setup script
- Installs to Program Files, creates Start Menu and desktop shortcuts
- Optional .toml file association
- Post-install launch option
- Built via `.\build.ps1 installer`

### Admin & Profiles
- **Per-tab admin indicator** — `[Admin]` badge on tab title when elevated
- **Profile Picker** now handles admin profiles (triggers UAC)
- **Profile Picker dialog** shows `[Admin]` badge
- **Window title** no longer shows `[Administrator]` — indicator is per-tab
- **Fixed duplicate tab** on admin launch (MainWindow accepts shell param)
- **Removed info dialog** before UAC prompt (UAC is sufficient)

### UI Improvements
- **Dynamic path label** — shows current working directory from shell prompt
- **Auto-expanding input** — grows from 28px to 120px as content increases
- **13 themes** — Monokai, Dracula, Nord, GitHub Dark, Catppuccin Mocha, etc.

### Docs
- Updated README.md, CHANGELOG.md, Roadmap.md for v1.3.0

---

## v1.2.0 — Session 3 (2026-07-20)

### Input Widget Redesign
- **Replaced QLineEdit with QTextEdit** for the input area — supports word wrap, multi-line display, and dynamic expansion for long commands
- **Path label** — "PS> " or "cmd> " indicator at the left of the input area shows current shell
- **Enter sends command**, Shift+Enter for newlines, Tab changes focus
- **Dynamic input height** — input area expands up to 120px for long lines, word wraps at widget width

### Themes
- **13 built-in themes** (up from 3): Added Monokai, Dracula, Nord, GitHub Dark, Catppuccin Mocha, Tomorrow Night, Gruvbox Dark, Tokyo Night, Rosé Pine, Zenburn

### Profile Management
- **Profile Management UI** — Table-based dialog for add/edit/duplicate/delete profiles (File → Manage Profiles, or + dropdown)
- **Run As Admin** — Each profile has an admin flag; triggers UAC via ShellExecuteW with "runas" verb
- **Edit Dialog** — Form-based editor for Name, Command, Arguments, Working Dir, Admin checkbox
- **Config persistence** — `Config.save()` writes profiles back to `settings.toml`
- **Default admin profiles** — `cmd_admin`, `powershell_admin` in settings.toml
- **Removed git_bash** from default profiles

### UI Improvements
- **"+" tab button** — Corner widget with dropdown listing all profiles, "Manage Profiles..." at bottom
- **RTL toggle** — Now propagates to both output QTextEdit and input QTextEdit
- **Word wrap** — Both output and input areas word-wrap at widget width

### Fixes
- **PowerShell doubled text** — CURSOR_POS handling for PSReadLine rewrites; `-NoProfile` flag
- **WSL encoding** — `wsl --list --verbose` UTF-16LE decoding fixed
- **Profile manager import error** — Missing QWidget import fixed

### Removed
- **Split panes** — Removed (didn't work with QWidget-based terminal)

---

## v1.1.0 — Session 2 (2026-07-20)

### Architecture
- **Rewrote TerminalWidget** from single QTextEdit to QWidget with QTextEdit (output) + QLineEdit (input)
- Moved all source files to `src/` directory

### Key Fixes
- Delete key, arrow keys, backspace all work correctly
- cls/clear/Clear-Host via ERASE_DISPLAY
- Exit command closes tab; last tab closes app
- PowerShell doubled text eliminated

### Tests
- 11 test suites, 100+ tests all passing

---

## v1.0.0 — Session 1 (2026-07-20)

### Initial release
- Multi-tab terminal with PTY (winpty), SSH, and serial support
- ANSI color rendering (256-color, RGB, bold, italic, underline)
- Mouse protocol support (xterm)
- Theme system, configuration via TOML
- Profile picker, split panes, search bar
- Font size controls, opacity toggle, RTL support
