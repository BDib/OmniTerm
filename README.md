# OmniTerm

A lightweight, extensible Windows terminal emulator built with Python, PyQt6, and `winpty`.

OmniTerm provides a clean, modern GUI wrapper around the Windows Pseudo Console (ConPTY) via `winpty`, giving you a fast terminal experience with a dark theme, ANSI stripping, and a thread-safe architecture designed for future extensibility (RTL text, theming, split panes, etc.).

---

## Features

- **Pseudo Console Backend** — Uses `winpty` to spawn and manage real shell processes (`cmd.exe`, PowerShell, WSL, etc.) with full PTY support.
- **3 Built-in Themes** — Campbell (default), Solarized Dark, and One Half Dark with `Ctrl+,` theme picker.
- **Dark Terminal Theme** — Campbell-inspired dark UI with `Cascadia Code` / `Consolas` monospace font.
- **ANSI Color Rendering** — Full SGR parser with 256-color and true-color (RGB) support, bold, italic, underline, inverse, and strikethrough.
- **Cursor Movement** — Handles `\x1b[A/B/C/D` (up/down/forward/back), `\x1b[H` (home), `\x1b[J` (clear screen), `\x1b[K` (clear line).
- **--plain Mode** — Strip all ANSI escapes for environments where color rendering isn't needed.
- **Thread-Safe I/O** — Dedicated reader and writer threads prevent blocking the GUI while communicating with the shell.
- **Configuration via TOML** — Simple `settings.toml` file for font, theme, opacity, cursor, and RTL behavior tuning.
- **RTL-Ready Architecture** — Built-in hooks for Arabic/Hebrew bidirectional text alignment.
- **Mouse Support** — xterm-compatible mouse tracking (`\x1b[?1000h`), click/scroll/hold encode to `\x1b[M` sequences.
- **Scroll Buffer** — Ring-buffer stores last 10,000 lines of styled output; scroll up/down to browse history.
- **Multi-Tab Interface** — `Ctrl+T` new tab, `Ctrl+W` close tab, `Ctrl+Tab` cycle tabs. Closable, movable tabs.
- **Split Panes** — `Ctrl+Shift+D` horizontal split, `Ctrl+Shift+\` vertical split. Each pane is an independent terminal.
- **Tab Titles** — Auto-derived from shell name (cmd, powershell, bash, etc.).
- **SSH Sessions** — `Ctrl+Shift+S` opens an SSH dialog for connecting to remote hosts with password or key-based auth.
- **Serial Console** — `Ctrl+Shift+R` opens a serial dialog for COM port connections (embedded/hardware work). Auto-detects available ports, configurable baud rate/parity/stop bits.
- **WSL Integration** — `Ctrl+Shift+U` auto-detects WSL distributions and opens a picker dialog. Each distribution opens in its own tab.
- **Named Profiles** — Define shell profiles in `settings.toml` (cmd, PowerShell, WSL, Git Bash) with `Ctrl+Shift+N` profile picker.
- **Custom Keybindings** — Remap shortcuts to built-in actions via `settings.toml`.
- **Find / Search** — `Ctrl+F` opens a search bar with match highlighting and navigation.
- **Minimal Footprint** — Pure Python with no native compilation required.
- **Copy & Paste** — `Ctrl+C` / `Ctrl+V` for clipboard integration.
- **Arrow Keys & Shortcuts** — Full arrow key, Home/End, Page Up/Down, and Ctrl组合 support.
- **Exit Detection** — Displays `[Process exited]` when the shell terminates.
- **Window Persistence** — Remembers window position and size across launches.
- **Font Shortcuts** — `Ctrl+=` / `Ctrl+-` to resize, `Ctrl+0` to reset, `Ctrl+Shift+T` to cycle themes.
- **Cursor Styles** — Configurable bar, block, or underline cursor with optional blinking.
- **Transparency Toggle** — `Ctrl+Shift+O` toggles between opaque and configured transparency.
- **PyInstaller Ready** — Build a standalone `.exe` with `build.bat`.
- **CI/CD Pipeline** — GitHub Actions runs tests on Python 3.10–3.13, builds and attaches `.exe` to releases on tag push.
- **CLI Arguments** — `--shell`, `--profile`, `--plain`, `--config`, `--version`.

---

## Project Structure

```
OmniTerm/
├── Main.py              # Application entry point — CLI args, profile/shell selection
├── config.py            # Configuration loader — profiles, keybindings, settings
├── themes.py            # Built-in themes — Campbell, Solarized Dark, One Half Dark
├── ansi_parser.py       # ANSI escape sequence parser (SGR, cursor, erase, OSC)
├── ansi_renderer.py     # Maps parsed spans → QTextCharFormat for styled rendering
├── mouse_handler.py     # xterm mouse protocol encoder (click/scroll/drag)
├── scroll_buffer.py     # Ring-buffer of styled lines with viewport tracking
├── search_bar.py        # Ctrl+F search bar with match highlighting
├── ssh_session.py       # SSH connection manager (paramiko wrapper)
├── ssh_dialog.py        # SSH connection dialog (host/port/user/pass/key)
├── serial_session.py    # Serial port connection manager (pyserial wrapper)
├── serial_dialog.py     # Serial connection dialog (port/baud/parity/stopbits)
├── wsl_manager.py       # WSL distribution detection and management
├── profile_picker.py    # Shell profile picker dialog
├── terminal_core.py     # TerminalEngine — local PTY + SSH + serial session management
├── terminal_ui.py       # PyQt6 UI — TerminalWidget, tabs, splits, shortcuts, mouse
├── settings.toml        # User configuration (profiles, keybindings, theme, cursor)
├── requirements.txt     # Python dependencies (PyQt6, paramiko, pyserial, pywinpty)
├── OmniTerm.spec        # PyInstaller spec — standalone .exe build
├── build.bat            # Build script — one-click packaging (release/debug/clean)
├── LICENSE              # MIT License
├── .gitignore           # Python/IDE/build ignores
├── .github/
│   └── workflows/
│       └── ci.yml       # GitHub Actions: test (3.10–3.13), lint, build, release
└── tests/
    ├── __init__.py
    ├── run_all.py           # Test runner (9 suites)
    ├── test_config.py       # Config loading tests (6 tests)
    ├── test_themes.py       # Theme system tests (8 tests)
    ├── test_ansi_parser.py  # ANSI parser tests (27 tests)
    ├── test_mouse_scroll.py # Mouse handler + scroll buffer tests (27 tests)
    ├── test_tabs.py         # Tab/split logic tests (6 tests)
    ├── test_profiles.py     # Profile/keybinding tests (12 tests)
    ├── test_distribution.py # CLI args, spec, CI workflow tests (11 tests)
    ├── test_ssh.py          # SSH session + dialog tests (9 tests)
    ├── test_serial_wsl.py   # Serial + WSL tests (15 tests)
    ├── nudge_test.py        # Diagnostic: PTY line endings (CRLF/CR)
    └── test_pty.py          # Diagnostic: full PTY spawn test
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
│  │ winpty Pty    │  │   │  - ANSI stripping          │
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
2. **Output** — The engine's reader thread reads from the PTY and emits `text_ready(str)` signals. The UI's `append_shell_text` slot strips ANSI codes and appends plain text.
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

# Or manually
pip install pyinstaller
pyinstaller OmniTerm.spec --noconfirm
```

The output will be at `dist/OmniTerm.exe`. This is a self-contained executable that does not require Python to be installed on the target machine.

```bash
# Debug build (console visible for troubleshooting)
build.bat debug
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI framework — widgets, signals/slots, styling |
| `pywinpty` | Python bindings for `winpty` — Windows PTY access |
| `toml` | Configuration file parsing |
| `python-bidi` | Bidirectional text algorithm (RTL support) |
| `arabic-reshaper` | Arabic ligature shaping for proper display |

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
theme = "campbell" # Future-proofing for color schemes
```

### Settings Reference

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `behavior` | `rtl_threshold` | `float` | `0.7` | Fraction of RTL characters needed to trigger right-to-left alignment |
| `ui` | `opacity` | `float` | `0.98` | Window opacity (0.0 = transparent, 1.0 = opaque) |
| `ui` | `font_family` | `string` | `"Cascadia Code"` | Monospace font family (fallback: Consolas) |
| `ui` | `font_size` | `int` | `14` | Font size in pixels |
| `ui` | `theme` | `string` | `"campbell"` | Color scheme name (reserved for future use) |

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

This opens a 1000×650 terminal window running `cmd.exe` (or the specified shell).

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

### Use a Different Shell

To launch with PowerShell, WSL, or another shell, modify the `engine.start()` call in `Main.py`:

```python
# PowerShell
engine.start(cmd='powershell.exe')

# WSL (Windows Subsystem for Linux)
engine.start(cmd='wsl.exe')

# Git Bash
engine.start(cmd='C:\\Program Files\\Git\\bin\\bash.exe')
```

---

## Testing

Unit tests cover configuration loading and the theme system:

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

## Diagnostics

Two test scripts are included for troubleshooting PTY issues:

### `test_pty.py` — Full PTY Diagnostic

Runs a comprehensive check: spawns a PTY, executes `dir`, verifies output file creation, and reports the OS/Python environment.

```bash
python test_pty.py
```

Sample output:
```
--- OmniTerm Diagnostic Tool ---
OS: Windows 10 (10.0.19045)
Python Version: 3.12.0 ...
Current Directory: C:\...\OmniTerm

[1] Attempting to spawn PTY with cmd.exe...
    Success: PTY process spawned.
[2] Executing command: dir > test.log
[3] Waiting 2 seconds for command completion...
[4] Checking for output file...
    Success: test.log found with 25 lines.
[5] Cleaning up...
    PTY terminated.
```

### `nudge_test.py` — Line Ending Test

Tests whether the PTY responds to CRLF (`\r\n`) or CR-only (`\r`) line endings:

```bash
python nudge_test.py
```

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

### ANSI Stripping

Terminal output often contains ANSI escape sequences (colors, cursor movement, etc.). Since OmniTerm renders plain text, these are stripped with a compiled regex:

```python
self.ansi_cleaner = re.compile(
    r'(?:\x1b\][0-9];.*?\x07|\x1b[@-_][0-?]*[ -/]*[@-~])'
)
```

Non-printable characters (below ASCII 32, except `\n`, `\r`, `\t`) are also filtered out.

### Key Event Forwarding

`TerminalWidget` subclasses `QTextEdit` but **overrides `keyPressEvent` without calling `super()`**. This prevents `QTextEdit` from inserting characters directly — instead, all keystrokes are forwarded to the PTY via `engine.write()`. The PTY's echo then produces the visible text.

---

## Extending OmniTerm

### Adding Color Support

Replace the ANSI stripper with a parser that maps SGR codes to `QTextCharFormat` objects. Use `QTextEdit.setExtraSelections()` or insert `QTextDocument` HTML for colored output.

### Split Panes

`MainWindow` can hold a `QSplitter` containing multiple `TerminalWidget` instances, each with its own `TerminalEngine`.

### RTL Text Rendering

The `settings.toml` already has `rtl_threshold` configured. Integration with `python-bidi` and `arabic-reshaper` is planned:

1. Detect RTL character ratio in each output line.
2. If ratio exceeds `rtl_threshold`, apply BiDi reordering.
3. Reshape Arabic text for proper ligature display.

### Theming

The `theme` setting in `settings.toml` is reserved for future color scheme support. Each theme would define foreground, background, cursor, and ANSI color mappings.

---

## Known Limitations

- **Windows Only** — `winpty` is Windows-specific. Cross-platform support would require `pexpect` (Linux/macOS) or a unified backend.
- **No ANSI Colors** — Output is plain text only. Color sequences are stripped rather than rendered.
- **No Scrollback History** — `QTextEdit` provides basic scrolling but no configurable history buffer.
- **No Tabbed Interface** — Single-window only. Tab support would require a `QTabWidget` wrapper.
- **Fixed Font** — Font is set in the stylesheet; runtime font switching is not implemented.

---

## License

This project does not currently include a license file. Contact the author for usage terms.
