# OmniTerm Optimization & Architectural Upgrades (Analysis & Recommendations)

We have performed a comprehensive analysis of OmniTerm and successfully implemented major, high-impact improvements to bring it closer to the performance and behavior of native console applications like the Windows Terminal, while incorporating mature, automatic Arabic shaping and Left-to-Right / Right-to-Left bidirectional layout support.

---

## 1. Architectural Highlights & Improvements

### 1.1 Unified Terminal Widget (Single QTextEdit)
* **Previous Design:** OmniTerm used a split pane: a read-only `_output` widget at the top and an active `_input` text edit box at the bottom. While this decoupled output from input, it felt clunky and differed significantly from standard terminal emulators.
* **Our Upgrade:** We replaced the separate panels with a single unified `TerminalScreen` (subclass of `QTextEdit`). All standard keyboard inputs (printable characters, carriage returns, backspaces, tabs, escape codes, arrows, and Ctrl combinations) are intercepted in the widget's `keyPressEvent` and forwarded directly to the backend shell PTY. The shell's echo and output are then printed at the cursor position on the screen.
* **Result:** A completely seamless, natural, single-widget interactive console experience exactly like Windows Terminal, Alacritty, or any other professional terminal application.

### 1.2 Automatic & Dynamic Arabic/RTL Support
* **Previous Design:** `rtl_threshold` was parsed but not actually used, and RTL was only toggleable manually without automatic contextual character joining or reordering.
* **Our Upgrade:** We added `arabic-reshaper` and `python-bidi` as core dependencies. Whenever new shell text is parsed and ready to be printed:
  1. We detect if the text contains any Arabic characters (Unicode range `0x0600 - 0x06FF`).
  2. If detected, we apply context-sensitive shaping via `arabic_reshaper.reshape` so that individual characters connect naturally into words.
  3. We then run the Unicode Bidirectional algorithm via `bidi.algorithm.get_display` so that mixed RTL and LTR text flows correctly.
  4. Block direction is dynamically configured to RTL/LTR based on active language or manual toggle.
* **Result:** Flawless out-of-the-box Arabic and mixed bidirectional text rendering.

### 1.3 True Cross-Platform Functionality (Unix PTY Integration)
* **Previous Design:** The backend engine was Windows-only, wrapping Windows ConPTY via `ctypes`.
* **Our Upgrade:** We implemented `UnixPTYEngine` using standard Python `pty` and `os` modules. When launched on non-Windows platforms (Linux, macOS), OmniTerm automatically detects the environment and spawns the system's default shell (e.g. `/bin/bash` or `/bin/zsh` or `$SHELL`).
* **Result:** OmniTerm is now fully cross-platform (Windows, Linux, macOS).

### 1.4 Native Path Startup & CWD Integration
* We introduced positional command-line argument parsing (`omniterm <path>`).
* We implemented smart directory resolution:
  * If `<path>` is specified and is a valid directory, OmniTerm opens directly in it.
  * If omitted and OmniTerm is launched from a terminal, it inherits and opens in the CWD (Current Working Directory).
  * If omitted and launched from its own installation folder (like a GUI shortcut), it automatically starts in the user's home folder / `%USERPROFILE%`.

---

## 2. Speeding Up Startup (Nuitka Optimization)

Nuitka compiles Python source code into native C before generating the executable, eliminating the Python interpreter's initialization and file extraction overhead (~13ms startup for Nuitka vs. ~100ms+ for PyInstaller).

We recommend using the following settings for the **fastest possible startup and smallest binary sizes** when compiling with Nuitka:

```powershell
python -m nuitka `
    --onefile `
    --enable-plugin=pyqt6 `
    --windows-console-mode=disable `
    --nofollow-import-to=tkinter,matplotlib,numpy,scipy,pandas,pytest,unittest `
    --output-filename=OmniTerm-windows-x64.exe `
    src/Main.py
```

### Recommendations for further local Nuitka speedups:
1. **Always Use MSVC compiler:** On Windows, Nuitka compiles faster and produces more optimized binaries when using Microsoft Visual C++ (MSVC) instead of MinGW.
2. **Utilize Nuitka Caching:** First-time compilations take longer (5-10 minutes) because Nuitka compiles C-wrapped files. Keep the cache directory (`C:\Temp\nbuild`) intact between local builds to speed up subsequent compilations significantly.

---

## 3. CI/CD Multi-Platform Pipeline

We updated and generalized `.github/workflows/ci.yml` so that whenever you push a version tag (`v*`), GitHub Actions automatically:
1. Tests the entire codebase across Python `3.11`, `3.12`, and `3.13`.
2. Generates standalone binary executables on:
   * **Windows x64** (PyInstaller + Inno Setup installer)
   * **Linux x64** (PyInstaller)
   * **macOS Intel x64** (PyInstaller)
   * **macOS Apple Silicon ARM64** (PyInstaller)
3. Automatically packages and zips/tarballs the compiled binaries into standard release formats (`.zip` for Windows & macOS, `.tar.gz` for Linux).
4. Creates a GitHub Release, naming the release as `OmniTerm <version>` and attaching the packaged binaries automatically!
