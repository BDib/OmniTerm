# OmniTerm

A modern, cross-platform terminal emulator built with Python and PyQt6.

OmniTerm provides a fast, lightweight terminal experience with native ConPTY integration on Windows, pty support on Linux/macOS, full ANSI color rendering, Arabic/bidirectional text support, dark themes, multi-tab interface, SSH/Serial/WSL integration, and a thread-safe architecture. Written in Python for rapid development and easy customization.

---

## Features

- **Unified Terminal Screen** — Single-widget terminal with native cursor and editing
- **ConPTY Backend** — Native Windows Pseudo Console API (no third-party PTY dependencies)
- **Cross-Platform PTY** — Windows (ConPTY), Linux/macOS (pty module)
- **Arabic Shaping + RTL** — Dynamic Arabic character reshaping and bidirectional text support
- **Full ANSI Color Rendering** — Complete SGR parser with 256-color and true-color (RGB) support, bold, italic, underline, inverse, strikethrough
- **13 Built-in Themes** — Campbell, Solarized Dark, One Half Dark, Monokai, Dracula, Nord, GitHub Dark, Catppuccin Mocha, Tomorrow Night, Gruvbox Dark, Tokyo Night, Rosé Pine, Zenburn
- **Profile Management** — Add, edit, duplicate, delete shell profiles with a table-based UI (File > Manage Profiles)
- **Run As Admin** — Each profile supports admin mode; triggers UAC and relaunches OmniTerm elevated
- **Multi-Tab Interface** — `Ctrl+T` new tab, `Ctrl+W` close tab, `Ctrl+Tab` cycle tabs
- **SSH Sessions** — `Ctrl+Shift+S` for remote hosts with password or key-based auth
- **Serial Console** — `Ctrl+Shift+R` for COM port connections
- **WSL Integration** — `Ctrl+Shift+U` auto-detects distributions
- **Mouse Support** — xterm-compatible mouse tracking
- **Find / Search** — `Ctrl+F` opens a search dialog
- **Copy & Paste** — `Ctrl+C` / `Ctrl+V` for clipboard integration
- **RTL Support** — Toggle window and line RTL direction
- **Window Persistence** — Remembers position and size across launches
- **Cursor Styles** — Configurable bar, block, or underline cursor
- **Transparency Toggle** — `Ctrl+Shift+O` toggles opacity
- **i18n** — English/Arabic language switching
- **CLI Arguments** — `--shell`, `--profile`, `--plain`, `--config`, `--version`, `--path`

---

## Project Structure

```
OmniTerm/
├── src/
│   ├── Main.py              # Application entry point
│   ├── config.py            # Configuration loader (profiles, keybindings, settings)
│   ├── themes.py            # 13 built-in themes
│   ├── ansi_parser.py       # ANSI escape sequence parser
│   ├── ansi_renderer.py     # Maps parsed spans → QTextCharFormat
│   ├── conpty.py            # ConPTY backend via ctypes (Windows)
│   ├── unix_pty.py          # Unix PTY backend via pty module (Linux/macOS)
│   ├── i18n.py              # Internationalization (English/Arabic)
│   ├── mouse_handler.py     # xterm mouse protocol encoder
│   ├── scroll_buffer.py     # Ring-buffer of styled lines
│   ├── search_bar.py        # Ctrl+F search dialog
│   ├── ssh_session.py       # SSH connection manager
│   ├── ssh_dialog.py        # SSH connection dialog
│   ├── serial_session.py    # Serial port manager
│   ├── serial_dialog.py     # Serial connection dialog
│   ├── wsl_manager.py       # WSL distribution detection
│   ├── profile_picker.py    # Shell profile picker dialog
│   ├── profile_manager.py   # Profile management UI (add/edit/delete)
│   ├── terminal_core.py     # TerminalEngine — PTY + SSH + serial sessions
│   ├── terminal_ui.py       # PyQt6 UI — TerminalScreen, tabs, menus
│   └── __init__.py
├── tests/                   # 12 test suites, 139 tests
├── installer/               # Inno Setup installer script
│   └── omniterm.iss
├── settings.toml            # User configuration
├── OmniTerm.spec            # PyInstaller spec
├── build.ps1 / build.bat    # Build scripts (Nuitka default)
├── CHANGELOG.md             # Version history
├── LICENSE                  # MIT License
└── .github/workflows/ci.yml # CI/CD pipeline
```

---

## Architecture

OmniTerm follows a clean **Engine / UI separation** pattern:

```
┌──────────────────────────────────────────────────────┐
│                     Main.py                          │
│   Creates QApplication, wires engine signals to UI   │
└──────────┬──────────────────────────┬────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────────┐   ┌────────────────────────────┐
│   TerminalEngine    │   │      MainWindow /           │
│   (terminal_core)   │   │   TerminalWidget (terminal_ui) │
│                     │   │                            │
│  ┌───────────────┐  │   │  QTextEdit subclass        │
│  │   ConPTY      │  │   │  - ANSI color rendering    │
│  │   Process     │  │   │  - Key event forwarding    │
│  └───────┬───────┘  │   │  - Dark theme styling      │
│          │          │   │                            │
│  ┌───────┴───────┐  │   │  append_shell_text(slot)   │
│  │ Reader Thread │──┼──▶│  ← connected via signal    │
│  └───────────────┘  │   │  keyPressEvent → engine    │
└─────────────────────┘   └────────────────────────────┘
```

### Data Flow

1. **Startup** — `Main.py` creates a `TerminalEngine` (spawns shell via ConPTY) and a `MainWindow`.
2. **Output** — The engine's reader thread reads from the ConPTY pipe and emits `text_ready(str)` signals. The UI's `append_shell_text` slot parses ANSI codes and renders styled text.
3. **Input** — `TerminalWidget` captures keystrokes in the input QTextEdit and forwards them to `engine.write()`, which queues data for the ConPTY pipe.
4. **Shutdown** — `engine.kill()` terminates the process and cleans up handles.

---

## Installation

### Prerequisites

- **Windows 10 build 17763+** (required for ConPTY)
- **Python 3.10+**
- **pip**

### Setup

```bash
# Clone the repository
git clone https://github.com/BDib/OmniTerm.git
cd OmniTerm

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python src/Main.py
```

### Running from Source

```bash
# Default (cmd.exe)
python src/Main.py

# Open with a specific shell
python src/Main.py --shell powershell.exe
python src/Main.py -s wsl.exe

# Open with a named profile
python src/Main.py --profile powershell
python src/Main.py -p wsl

# With a custom config file
python src/Main.py --config path/to/settings.toml

# Disable ANSI color rendering (strip all escapes)
python src/Main.py --plain

# Show version
python src/Main.py --version
```

---

## Building

### Quick Start

```powershell
# Default build (Nuitka — fastest)
.\build.ps1

# Or with cmd
build.bat
```

### Build Options

| Command | Description |
|---------|-------------|
| `.\build.ps1` | Nuitka standalone build (default) |
| `.\build.ps1 pyinstaller` | PyInstaller standalone build |
| `.\build.ps1 debug` | Nuitka debug build (console visible) |
| `.\build.ps1 pyinstaller-debug` | PyInstaller debug build |
| `.\build.ps1 installer` | Nuitka build + Inno Setup installer |
| `.\build.ps1 clean` | Remove all build artifacts |

### Nuitka vs PyInstaller

| | Nuitka | PyInstaller |
|---|---|---|
| **Startup** | ~13ms | ~97ms |
| **Size** | ~25 MB | ~44 MB |
| **Build time** | ~5-10 min (first run) | ~30s |
| **Default** | Yes | Fallback |

### Output Files

| File | Builder | Description |
|------|---------|-------------|
| `dist\OmniTerm-win10-x64.exe` | Nuitka | Standalone executable |
| `dist\pyOmniTerm-win10-x64.exe` | PyInstaller | Standalone executable |
| `installer_output\OmniTermSetup-win10-x64.exe` | Inno Setup | Windows installer |

### Creating an Installer

```powershell
# Build + create installer (requires Inno Setup 6)
.\build.ps1 installer
```

The installer includes:
- Installation to Program Files
- Start Menu and desktop shortcuts
- Optional .toml file association
- Uninstaller
- Post-install launch option

---

## Testing

```bash
# Run all tests (141 tests across 12 suites)
python -m pytest tests/ -v

# Run a specific test module
python -m pytest tests/test_ansi_parser.py -v
python -m pytest tests/test_config.py -v

# Run with quiet output
python -m pytest tests/ -q
```

### Test Coverage

| Module | Tests | What's Tested |
|--------|-------|---------------|
| `test_ansi_parser.py` | 28 | Text, newlines, tabs, SGR (bold/color/256/RGB/reset), cursor movement, erase, OSC, strip_ansi, mouse mode |
| `test_config.py` | 6 | Default values, file override, partial override, malformed TOML, behavior section |
| `test_distribution.py` | 11 | Version string, CLI args, spec/build/CI files |
| `test_keyboard.py` | 14 | Type/enter, engine state, rendering, input editing, focus, history, themes, path label |
| `test_mouse_scroll.py` | 27 | Mouse enable/disable/priority, press/release/motion/scroll encoding, scroll buffer |
| `test_profiles.py` | 12 | Profile dataclass, config loading, keybindings, action resolution |
| `test_rendering.py` | 7 | CR handling, ERASE_DISPLAY, ERASE_LINE, plain mode |
| `test_serial_wsl.py` | 15 | Serial session, serial dialog, WSL manager, terminal engine |
| `test_ssh.py` | 9 | SSH session, SSH dialog, terminal engine SSH, keybindings |
| `test_tabs.py` | 6 | Shell title, tab engines, index management, split orientation |
| `test_themes.py` | 8 | Theme listing, lookup, ANSI colors, stylesheet generation |

---

## Configuration

OmniTerm reads settings from `settings.toml` on startup. If missing, it auto-creates one with sensible defaults.

### Settings Reference

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `behavior` | `rtl_threshold` | float | `0.7` | Fraction of RTL characters needed for right-to-left alignment |
| `ui` | `opacity` | float | `0.98` | Window opacity (0.0 = transparent, 1.0 = opaque) |
| `ui` | `font_family` | string | `"Cascadia Code"` | Monospace font (fallback: Consolas) |
| `ui` | `font_size` | int | `14` | Font size in pixels |
| `ui` | `theme` | string | `"campbell"` | Color scheme (campbell, solarized_dark, dracula, nord, ...) |
| `ui` | `cursor_style` | string | `"bar"` | Cursor style: bar, block, or underline |
| `ui` | `cursor_blink` | bool | `true` | Whether the cursor blinks |
| `default_profile` | — | string | `"cmd"` | Default shell profile |
| `profiles.*` | `command` | string | — | Shell executable |
| `profiles.*` | `args` | list | `[]` | Command-line arguments |
| `profiles.*` | `admin` | bool | `false` | Run as Administrator |

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Execute command | `Enter` |
| Copy selected text | `Ctrl+C` |
| Paste from clipboard | `Ctrl+V` |
| Arrow up/down | `Up` / `Down` (history in most shells) |
| Word forward/back | `Ctrl+Right` / `Ctrl+Left` |
| Home / End | `Home` / `End` |
| Page Up / Page Down | `PageUp` / `PageDown` |
| Clear screen | `Ctrl+L` |
| Interrupt (SIGINT) | `Ctrl+C` (when no text selected) |
| EOF | `Ctrl+D` |
| Suspend | `Ctrl+Z` |
| Kill to end of line | `Ctrl+K` |
| Kill to start of line | `Ctrl+U` |
| Delete word | `Ctrl+W` |
| Home (Ctrl) | `Ctrl+A` |
| End (Ctrl) | `Ctrl+E` |
| Increase font size | `Ctrl+=` |
| Decrease font size | `Ctrl+-` |
| Reset font size | `Ctrl+0` |
| Cycle theme | `Ctrl+Shift+T` |
| Theme picker dialog | `Ctrl+,` |
| Toggle transparency | `Ctrl+Shift+O` |
| New tab | `Ctrl+T` |
| Close tab | `Ctrl+W` |
| Next tab | `Ctrl+Tab` |
| Previous tab | `Ctrl+Shift+Tab` |
| Profile picker | `Ctrl+Shift+N` |
| SSH Connect | `Ctrl+Shift+S` |
| Serial Connect | `Ctrl+Shift+R` |
| WSL Connect | `Ctrl+Shift+U` |
| Find/Search | `Ctrl+F` |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI framework — widgets, signals/slots, styling |
| `toml` | Configuration file parsing |
| `paramiko` | SSH client library for remote connections |
| `pyserial` | Serial port communication for hardware/embedded work |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
