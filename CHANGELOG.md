# Changelog

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
