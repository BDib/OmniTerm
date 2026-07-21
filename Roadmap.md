# OmniTerm Roadmap

A Windows-focused development plan for building OmniTerm into a full-featured terminal emulator.

---

## Phase 1 — Stability & Polish (v0.2) ✅

> Make what exists rock-solid before adding features.

### 1.1 Configuration Loading

- [x] Actually load `settings.toml` at startup and apply values (font, size, opacity, RTL threshold).
- [x] Add a `--config <path>` CLI flag to specify an alternate config file.
- [x] Gracefully handle missing/malformed config — fall back to defaults with a warning.

### 1.2 Window Improvements

- [x] Save and restore window position/size across launches (store in `%APPDATA%/OmniTerm/state.toml`).
- [ ] Set window icon (create a proper `.ico` asset).
- [x] Add a minimum window size constraint so the terminal can't be resized to zero.

### 1.3 Process Robustness

- [x] Detect PTY process exit and display `[Process exited]` in the terminal instead of going silent.
- [x] Handle PTY spawn failures with a user-facing error dialog instead of a bare exception.
- [x] Add a "Restart Shell" action (`Ctrl+Shift+R`) that kills and respawns the PTY.

### 1.4 Copy & Paste

- [x] Enable `Ctrl+C` to copy selected text when text is selected, and send `SIGINT`-equivalent when nothing is selected.
- [x] Enable `Ctrl+V` to paste from the Windows clipboard into the PTY.
- [ ] Add `Ctrl+Shift+C` / `Ctrl+Shift+V` as alternative copy/paste shortcuts.

### 1.5 PyInstaller Packaging

- [x] Create `OmniTerm.spec` and `build.bat` for PyInstaller.
- [x] Embed `settings.toml` alongside the executable (bundled into the `.spec` as data).
- [x] Test the packaged `.exe` on a clean Windows machine with no Python installed.
- [x] Add version number to the window title (e.g., `OmniTerm v1.0.0`).

---

## Phase 2 — Theming & Customization (v0.3) ✅

> Make it look and feel like *your* terminal.

### 2.1 Color Themes

- [x] Define a theme schema: `background`, `foreground`, `cursor`, `selection`, and 16 ANSI colors.
- [x] Ship 3 built-in themes: **Campbell** (dark), **Solarized Dark**, **One Half Dark**.
- [x] Load theme from `settings.toml` and apply via `QTextEdit.setStyleSheet()`.
- [x] Add a `Ctrl+,` shortcut to open a theme picker dialog.

### 2.2 Font Selection

- [x] Read `font_family` and `font_size` from config and apply at startup.
- [x] Add `Ctrl+=` / `Ctrl+-` for font size increase/decrease.
- [x] Add `Ctrl+0` to reset font size to default.
- [ ] Enumerate installed monospace fonts on the system for a font picker.

### 2.3 Cursor Customization

- [x] Support block, underline, and vertical-bar cursor styles (configurable).
- [x] Add blinking cursor with configurable blink rate.
- [ ] Respect the Windows system cursor blink rate setting.

### 2.4 Transparency

- [x] Apply `opacity` from config to the main window.
- [x] Add `Ctrl+Shift+O` to toggle between opaque and configured transparency.

---

## Phase 3 — ANSI Rendering (v0.4) ✅

> Colors. The terminal needs colors.

### 3.1 SGR Parser

- [x] Build a lightweight ANSI CSI/SGR parser.
- [x] Parse `\x1b[...m` sequences into attributes: bold, italic, underline, strikethrough, inverse.
- [x] Map the 8 basic ANSI colors + bright variants to the theme's color palette.
- [x] Map 256-color and true-color (`\x1b[38;2;r;g;b m`) sequences.

### 3.2 Cursor Movement

- [x] Handle cursor movement escape sequences: `\x1b[nA` (up), `\x1b[nB` (down), `\x1b[nC` (forward), `\x1b[nD` (back).
- [x] Handle `\x1b[2J` (clear screen) and `\x1b[K` (clear line).
- [x] Handle `\x1b[H` (cursor home) and `\x1b[n;mH` (cursor position).

### 3.3 Rendering Pipeline

- [x] Replace plain-text `insertPlainText` with `QTextCursor` + `QTextCharFormat` based rendering.
- [x] Each styled span gets its own format (foreground color, background color, bold, etc.).
- [x] Measure and optimize for large output (e.g., `dir /s` producing thousands of lines).

### 3.4 Fallback

- [x] Keep the ANSI-stripping fallback as a `--plain` CLI flag for environments where full rendering isn't needed.

---

## Phase 4 — Advanced Input (v0.5) ✅

> Make the terminal feel native.

### 4.1 Keyboard Handling

- [x] Support arrow keys: send `\x1b[A` (up), `\x1b[B` (down), `\x1b[C` (right), `\x1b[D` (left).
- [x] Support `Home`/`End` (`\x1b[H` / `\x1b[F`), `Page Up`/`Page Down`.
- [x] Support `Ctrl+Arrow` for word-by-word navigation (`\x1b[1;5A`, etc.).
- [x] Support `Ctrl+L` (clear screen), `Ctrl+D` (EOF), `Ctrl+Z` (suspend on Windows).

### 4.2 Mouse Support

- [x] Enable mouse tracking mode (`\x1b[?1000h`).
- [x] Send mouse position as `\x1b[M` escape sequences on click/hover/scroll.
- [x] Enable scroll-wheel to send `\x1b[A`/`\x1b[B` (up/down line) when the shell is in alternate screen mode.

### 4.3 Selection & Scrolling

- [x] Implement proper text selection with Shift+Click and Shift+Arrow keys.
- [x] Implement scroll buffer (ring-buffer stores last 10,000 lines of styled output).
- [ ] Add a scrollbar widget.

---

## Phase 5 — Multi-Tab & Split Panes (v0.6) ✅

> One window, many shells.

### 5.1 Tabbed Interface

- [x] Replace single `TerminalWidget` with a `QTabWidget` container.
- [x] Each tab gets its own `TerminalEngine` instance.
- [x] `Ctrl+T` to open a new tab, `Ctrl+W` to close the current tab.
- [x] `Ctrl+Tab` / `Ctrl+Shift+Tab` to cycle tabs.
- [x] Show process name (e.g., `cmd`, `powershell`) as the tab title.

### 5.2 Split Panes

- [x] `Ctrl+Shift+D` to split horizontally, `Ctrl+Shift+\` to split vertically.
- [x] Each pane is an independent `TerminalWidget` + `TerminalEngine`.
- [ ] `Alt+Arrow` to move focus between panes.
- [ ] Drag-and-drop to reorder panes.

### 5.3 Session Persistence

- [ ] Save open tabs/panes layout to `%APPDATA%/OmniTerm/sessions/<name>.toml`.
- [ ] Restore last session on launch (optional, configurable).

---

## Phase 6 — Profile & Plugin System (v0.7) ✅

> Power user features.

### 6.1 Profiles

- [x] Define named profiles in `settings.toml` (cmd, powershell, pwsh, wsl, git_bash).
- [x] `Ctrl+Shift+N` to open a new tab with a profile picker.
- [x] Set a default profile in config.

### 6.2 Keybindings

- [x] Define custom keybindings in `settings.toml`.
- [x] Built-in actions: `find`, `new_tab`, `close_tab`, `split_horizontal`, `split_vertical`, `font_bigger`, `font_smaller`, `theme_cycle`, `theme_picker`, `toggle_opacity`, `copy`, `paste`, `profile_picker`, `ssh_connect`, `serial_connect`, `wsl_connect`.

### 6.3 Find / Search

- [x] `Ctrl+F` opens a search bar at the bottom of the terminal.
- [x] Search through the scrollback buffer and highlight matches.
- [ ] `F3` / `Shift+F3` to jump to next/previous match.

---

## Phase 7 — Distribution & CI (v0.8) ✅

> Make it easy for everyone to use.

### 7.1 PyInstaller Finalization

- [x] Create a proper `.spec` file with data bundling and metadata.
- [x] Embed `settings.toml` as default config in the package.
- [x] Add command-line arguments: `--version`, `--config`, `--plain`, `--shell <cmd>`.
- [x] Test the `.exe` on Windows 10 and Windows 11.

### 7.2 Auto-Update

- [ ] Check GitHub releases for new versions on startup (opt-in).
- [ ] Prompt the user to download and install the update.

### 7.3 CI/CD

- [x] GitHub Actions workflow: on tag push → build `.exe` with PyInstaller → attach to GitHub Release.
- [x] Matrix: test on Python 3.10, 3.11, 3.12, 3.13.
- [x] Lint with `ruff`, type-check with `mypy`.

---

## Phase 8 — SSH Sessions (v0.9) ✅

### 8.1 SSH Client

- [x] `Ctrl+Shift+S` opens an SSH connection dialog.
- [x] Support password and key-based authentication.
- [x] Each SSH session opens in its own tab.

---

## Phase 9 — Serial + WSL (v1.0) ✅

### 9.1 Serial Console

- [x] `Ctrl+Shift+R` opens a serial connection dialog (port, baud rate, data bits, parity, stop bits).
- [x] Auto-detect available COM ports.
- [x] Support DTR/RTS flow control signals.

### 9.2 WSL Integration

- [x] Auto-detect installed WSL distributions.
- [x] `Ctrl+Shift+U` opens a distribution picker dialog.
- [x] Each WSL distribution opens in its own tab.

---

## Future Ideas

| Feature | Description |
|---------|-------------|
| **Session Recording** | Record terminal sessions to `.cast` files (asciinema-compatible) |
| **Plugin API** | Python plugin system for custom extensions |
| **GPU Acceleration** | Migrate rendering to a QOpenGLWidget for massive output |
| **Font Picker** | Enumerate installed monospace fonts and let user pick |
| **F3 Search Navigation** | `F3` / `Shift+F3` for next/previous match in search bar |
| **Quake Mode** | `Ctrl+~` dropdown terminal (like console/tilda on Linux) |
| **ConPTY Backend** | Replace winpty with Windows ConPTY for better compatibility |
| **Tab Splits** | Reimplement split panes with proper QWidget-based rendering |
| **Custom Prompts** | Per-profile custom prompt configuration |
| **Tab Rename** | Right-click tab to rename |

---

## Versioning

| Version | Milestone | Status |
|---------|-----------|--------|
| `v0.2` | Stability & Polish | ✅ Done |
| `v0.3` | Theming | ✅ Done |
| `v0.4` | ANSI Rendering | ✅ Done |
| `v0.5` | Advanced Input | ✅ Done |
| `v0.6` | Multi-Tab & Splits | ✅ Done (splits removed in v1.2) |
| `v0.7` | Profiles & Plugins | ✅ Done |
| `v0.8` | Distribution | ✅ Done |
| `v0.9` | SSH Sessions | ✅ Done |
| `v1.0` | Serial + WSL | ✅ Done |
| `v1.1` | Widget Rewrite | ✅ Done |
| `v1.2` | Profile Management & Themes | ✅ Done |
| `v1.3` | Nuitka Build & Installer | ✅ Done |
| `v1.4` | CI Nuitka + Win10/11 x64 Release | ✅ Done |
| `v1.5` | Search/F3 + Docs + Menu Cleanup | ✅ Done |
| `v1.6` | Config Fallback + Search Dialog Fix + Input Fix | ✅ Done |
| `v2.0` | ConPTY Backend + Source Optimization | ✅ Done |
