# OmniTerm

A lightweight, extensible Windows terminal emulator built with Python, PyQt6, and `winpty`.

OmniTerm provides a clean, modern GUI wrapper around the Windows Pseudo Console via `winpty`, giving you a fast terminal experience with full ANSI color rendering, dark themes, multi-tab support, SSH/Serial/WSL integration, and a thread-safe architecture.

---

## Features

- **Dual-Pane Terminal** — Separate output display (QTextEdit) and input editor (QTextEdit) with native cursor and editing
- **Full ANSI Color Rendering** — Complete SGR parser with 256-color and true-color (RGB) support, bold, italic, underline, inverse, strikethrough
- **13 Built-in Themes** — Campbell, Solarized Dark, One Half Dark, Monokai, Dracula, Nord, GitHub Dark, Catppuccin Mocha, Tomorrow Night, Gruvbox Dark, Tokyo Night, Rosé Pine, Zenburn
- **Command History** — Up/Down arrows in the input field cycle through previously entered commands
- **Native Input Editing** — Left/Right/Home/End/Delete/Backspace all work via QTextEdit's built-in handling
- **Profile Management** — Add, edit, duplicate, delete shell profiles with a table-based UI (File → Manage Profiles)
- **Run As Admin** — Each profile supports admin mode; triggers UAC and relaunches OmniTerm elevated
- **"+" Tab Button** — Corner widget with dropdown listing all profiles for quick tab creation
- **ERASE_DISPLAY** — `cls`/`clear`/`Clear-Host` properly clears the output widget
- **CURSOR_POS Handling** — Handles PSReadLine rewrites (cursor movement + overwrite for PowerShell)
- **Multi-Tab Interface** — `Ctrl+T` new tab, `Ctrl+W` close tab, `Ctrl+Tab` cycle tabs
- **SSH Sessions** — `Ctrl+Shift+S` for remote hosts with password or key-based auth
- **Serial Console** — `Ctrl+Shift+R` for COM port connections
- **WSL Integration** — `Ctrl+Shift+U` auto-detects distributions, UTF-16LE decoding fixed
- **Mouse Support** — xterm-compatible mouse tracking
- **Find / Search** — `Ctrl+F` opens a search bar
- **Copy & Paste** — `Ctrl+C` / `Ctrl+V` for clipboard integration
- **RTL Support** — Toggle window and line RTL direction
- **Window Persistence** — Remembers position and size across launches
- **Cursor Styles** — Configurable bar, block, or underline cursor
- **Transparency Toggle** — `Ctrl+Shift+O` toggles opacity
- **PyInstaller Ready** — Build standalone `.exe` with `build.bat` or `.\build.ps1`
- **CI/CD Pipeline** — GitHub Actions tests on Python 3.10–3.13
- **CLI Arguments** — `--shell`, `--profile`, `--plain`, `--config`, `--version`

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
│   ├── mouse_handler.py     # xterm mouse protocol encoder
│   ├── scroll_buffer.py     # Ring-buffer of styled lines
│   ├── search_bar.py        # Ctrl+F search bar
│   ├── ssh_session.py       # SSH connection manager
│   ├── ssh_dialog.py        # SSH connection dialog
│   ├── serial_session.py    # Serial port manager
│   ├── serial_dialog.py     # Serial connection dialog
│   ├── wsl_manager.py       # WSL distribution detection
│   ├── profile_picker.py    # Shell profile picker dialog
│   ├── profile_manager.py   # Profile management UI (add/edit/delete)
│   ├── terminal_core.py     # TerminalEngine — PTY + SSH + serial sessions
│   ├── terminal_ui.py       # PyQt6 UI — TerminalWidget, tabs, menus
│   └── __init__.py
├── tests/                   # 11 test suites, 100+ tests
├── settings.toml            # User configuration
├── OmniTerm.spec            # PyInstaller spec
├── build.bat / build.ps1    # Build scripts
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
│  │ winpty Pty    │  │   │  - ANSI color rendering    │
│  │   Process     │  │   │  - Key event forwarding    │
│  └───────┬───────┘  │   │  - Dark theme styling      │
│          │          │   │                            │
│  ┌───────┴───────┐  │   │  append_shell_text(slot)   │
│  │ Reader Thread │──┼──▶│  ← connected via signal    │
│  │ Writer Thread │◀─┼───│  keyPressEvent → engine    │
│  └───────────────┘  │   └────────────────────────────┘
└─────────────────────┘
```

### Data Flow

1. **Startup** — `Main.py` creates a `TerminalEngine` (spawns `cmd.exe` via `winpty`) and a `MainWindow`.
2. **Output** — The engine's reader thread reads from the PTY and emits `text_ready(str)` signals. The UI's `append_shell_text` slot parses ANSI codes and renders styled text.
3. **Input** — `TerminalWidget.keyPressEvent` captures keystrokes and forwards them to `engine.write()`, which queues data for the writer thread to send to the PTY.
4. **Shutdown** — `engine.kill()` terminates the PTY process and stops both threads.

---

## Installation

### Prerequisites

- **Windows 10+** (required for `winpty` / ConPTY)
- **Python 3.10+**
- **pip**

### Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd OmniTerm

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python Main.py
```

### Building a Standalone `.exe`

OmniTerm can be packaged into a single Windows executable using PyInstaller:

```bash
# Quick build (double-click build.bat)
build.bat

# Or with PowerShell
.\build.ps1

# Or manually
pip install pyinstaller
pyinstaller OmniTerm.spec --noconfirm
```

The output will be at `dist/OmniTerm.exe`. This is a self-contained executable that does not require Python to be installed on the target machine.

```bash
# Debug build (console visible for troubleshooting)
build.bat debug
.\build.ps1 debug
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI framework — widgets, signals/slots, styling |
| `pywinpty` | Python bindings for `winpty` — Windows PTY access |
| `toml` | Configuration file parsing |
| `python-bidi` | Bidirectional text algorithm (RTL support) |
| `arabic-reshaper` | Arabic ligature shaping for proper display |
| `paramiko` | SSH client library for remote connections |
| `pyserial` | Serial port communication for hardware/embedded work |

---

## Configuration

OmniTerm reads settings from `settings.toml` on startup:

```toml
# OmniTerm Configuration File

[behavior]
# Sensitivity for automatic RTL alignment (0.0 to 1.0)
# 0.7 means a line must be 70% Arabic/Hebrew to flip to the right
rtl_threshold = 0.7

[ui]
# Window appearance
opacity = 0.98
font_family = "Cascadia Code"
font_size = 14
theme = "campbell"

# Cursor style: "bar" | "block" | "underline"
cursor_style = "bar"
# Whether the cursor blinks
cursor_blink = true

# Shell profiles
default_profile = "cmd"

[profiles.cmd]
command = "cmd.exe"

[profiles.powershell]
command = "powershell.exe"
args = ["-NoLogo"]

[profiles.wsl]
command = "wsl.exe"

# Custom keybindings
[keybindings]
"Ctrl+Shift+N" = "profile_picker"
"Ctrl+Shift+F" = "find"
```

### Settings Reference

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `behavior` | `rtl_threshold` | `float` | `0.7` | Fraction of RTL characters needed to trigger right-to-left alignment |
| `ui` | `opacity` | `float` | `0.98` | Window opacity (0.0 = transparent, 1.0 = opaque) |
| `ui` | `font_family` | `string` | `"Cascadia Code"` | Monospace font family (fallback: Consolas) |
| `ui` | `font_size` | `int` | `14` | Font size in pixels |
| `ui` | `theme` | `string` | `"campbell"` | Color scheme name (campbell, solarized_dark, one_half_dark) |
| `ui` | `cursor_style` | `string` | `"bar"` | Cursor style: bar, block, or underline |
| `ui` | `cursor_blink` | `bool` | `true` | Whether the cursor blinks |

---

## Usage

### Launch

```bash
python Main.py

# Open with a specific shell
python Main.py --shell powershell.exe
python Main.py -s wsl.exe

# Open with a named profile
python Main.py --profile powershell
python Main.py -p wsl

# With a custom config file
python Main.py --config path/to/settings.toml

# Disable ANSI color rendering (strip all escapes)
python Main.py --plain

# Show version
python Main.py --version
```

This opens a 1000x650 terminal window running `cmd.exe` (or the specified shell).

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Type commands | Just type — input is forwarded to the PTY |
| Execute | `Enter` |
| Backspace | `Backspace` |
| Tab completion | `Tab` |
| Delete forward | `Delete` |
| Copy selected text | `Ctrl+C` |
| Paste from clipboard | `Ctrl+V` |
| Arrow up/down | `Up` / `Down` (history in most shells) |
| Arrow left/right | `Left` / `Right` (cursor movement) |
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
| Escape | `Esc` |
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
| Split horizontal | `Ctrl+Shift+D` |
| Split vertical | `Ctrl+Shift+\` |
| Profile picker | `Ctrl+Shift+N` |
| SSH Connect | `Ctrl+Shift+S` |
| Serial Connect | `Ctrl+Shift+R` |
| WSL Connect | `Ctrl+Shift+U` |
| Find/Search | `Ctrl+F` |

---

## Testing

```bash
# Run all tests
python tests/run_all.py

# Run specific test module
python tests/test_config.py
python tests/test_themes.py
```

### Test Coverage

| Module | Tests | What's Tested |
|--------|-------|---------------|
| `test_config.py` | 6 | Default values, file override, partial override, malformed TOML, behavior section |
| `test_themes.py` | 8 | Theme listing, lookup, case-insensitivity, fallback, ANSI colors, stylesheet generation |
| `test_ansi_parser.py` | 27 | Text, newlines, tabs, SGR (bold/color/256/RGB/reset), cursor movement, erase, OSC title, strip_ansi, indexed colors, mouse mode |
| `test_mouse_scroll.py` | 27 | Mouse enable/disable/priority, press/release/motion/scroll encoding, scroll buffer capacity/viewport/scroll/clear |
| `test_tabs.py` | 6 | Shell title derivation, tab engine tracking, index management, split orientations |
| `test_profiles.py` | 12 | Profile dataclass, config loading, get_shell_command, keybindings, action resolution |
| `test_distribution.py` | 11 | Version string, CLI args (--help/--version/--shell/--profile/--plain/--config), spec/build/CI files |
| `test_ssh.py` | 9 | SSHSession import/defaults/params, SSHDialog import, TerminalEngine SSH, BUILTIN_ACTIONS, close/resize safety |
| `test_serial_wsl.py` | 15 | SerialSession import/defaults/params/close/ports, SerialDialog baud rates, WSLManager availability/distributions/commands/shells, TerminalEngine serial |

---

## How It Works (Technical Deep Dive)

### PTY via winpty

Windows does not have a native POSIX PTY. `winpty` bridges this gap by creating a hidden console process and providing a pipe-based interface that mimics PTY behavior. OmniTerm uses `PtyProcess.spawn()` to start a shell and communicates via `.read()` / `.write()` on the pipe.

### Thread Architecture

The engine runs two daemon threads to avoid blocking the PyQt6 event loop:

| Thread | Function | Timeout |
|--------|----------|---------|
| **Reader** | Polls `pty.read(1024)` in a loop, emits `text_ready` signal | 10ms sleep between reads |
| **Writer** | Dequeues from `input_queue`, writes to `pty.write()` | 100ms queue timeout |

Both threads exit when `engine.alive` is set to `False`.

### ANSI Rendering

Terminal output contains ANSI escape sequences for colors, cursor movement, and styling. OmniTerm parses these with a custom regex-based parser (`ansi_parser.py`) that emits `Span` objects, then maps each span to a `QTextCharFormat` for styled rendering in the `QTextEdit`. Supports:

- 8 basic ANSI colors + 8 bright variants (mapped to theme palette)
- 256-color indexed palette
- True-color RGB (`\x1b[38;2;r;g;b m`)
- Bold, dim, italic, underline, strikethrough, inverse

### Key Event Forwarding

`TerminalWidget` subclasses `QTextEdit` but **overrides `keyPressEvent` without calling `super()`**. This prevents `QTextEdit` from inserting characters directly — instead, all keystrokes are forwarded to the PTY via `engine.write()`. The PTY's echo then produces the visible text.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
