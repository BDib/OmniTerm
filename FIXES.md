# Known Issues & Fixes — Session Log

## Current Critical Issue: cmd.exe exits after 5 seconds

### Symptoms
- App starts, PTY spawns, but cmd.exe exits after exactly 5 seconds
- Event loop ends immediately after PTY exits
- Terminal appears blank, user sees no prompt
- `errors.txt` shows: `PTY reached EOF (process exited)` then `Event loop ended, status=0`

### Evidence from errors.txt
```
[13:17:16] PTY spawned, pid=11728
[13:17:16] Reader thread started
[13:17:21] PTY reached EOF (process exited)    ← exactly 5s later
[13:17:21] Event loop ended, status=0
```

### Root Cause Analysis

**Theory 1: cmd.exe exits because winpty pipe is broken**
- winpty spawns cmd.exe, but the PTY pipe might not be properly connected
- cmd.exe tries to read from stdin, gets EOF, and exits
- The 5-second delay is cmd.exe waiting for input before timing out

**Theory 2: Race condition in startup**
- The app creates MainWindow, starts PTY, shows window — but the window might not be fully rendered before cmd.exe starts
- The PTY output might be lost because the widget isn't ready to receive it

**Theory 3: Nuitka onefile build issue**
- `sys.frozen = False` in the Nuitka build (verified in errors.txt)
- This might affect winpty's behavior or path resolution
- The onefile extraction to temp directory might interfere with winpty's pipe creation

### What We've Tried
1. ✅ Added `--verbose` flag for debugging
2. ✅ Added comprehensive error logging to errors.txt
3. ✅ Fixed config path resolution for onefile builds
4. ✅ Auto-create settings.toml with default profiles
5. ❌ Switched to Nuitka onefile mode (still same issue)
6. ❌ Added `setReadOnly(True)`/`setReadOnly(False)` toggling (cursor issues)

### What Needs to Be Done

#### Priority 1: Fix winpty PTY connection
- The PTY spawns but cmd.exe exits after 5 seconds
- Need to verify winpty pipe is properly connected
- Check if `PtyProcess.spawn()` is being called with correct arguments
- Try using `conpty` instead of `winpty` (Windows 10 1809+ has built-in conpty)
- Check winpty version compatibility (we have winpty 3.0.5)

#### Priority 2: Fix Nuitka frozen detection
- `sys.frozen = False` in Nuitka onefile builds
- This breaks config path resolution and any frozen-specific code
- Need to manually set `sys.frozen = True` or use a different detection method

#### Priority 3: Fix cursor visibility
- `setReadOnly(True)` hides the cursor
- `setReadOnly(False)` causes QTextEdit internal handling to interfere
- Need a different approach — possibly a custom cursor widget overlay

#### Priority 4: Fix terminal rendering
- CR (carriage return) handling causes doubled text
- ERASE_DISPLAY works for cls/clear
- CURSOR_POS handling for PSReadLine rewrites partially works

### Architecture Notes

**Why Python?** The project uses Python specifically for:
- `arabic-reshaper` — Arabic text reshaping for RTL support
- `python-bidi` — Bidirectional text algorithm
- Python's RTL handling is more mature than Go/Zig alternatives

**Terminal architecture:**
- QTextEdit for output (read-only, append-only)
- QLineEdit for input (native editing)
- winpty for PTY access
- ANSI parser for escape sequence handling
- Thread-safe I/O (reader/writer threads)

**Build system:**
- Nuitka (default, fastest startup) — onefile mode
- PyInstaller (fallback) — standalone mode
- Inno Setup installer
- GitHub Actions CI/CD

### Files Modified This Session
- `src/terminal_core.py` — Added comprehensive error logging
- `src/Main.py` — Added --verbose flag, error logging, frozen detection
- `src/config.py` — Fixed path resolution, auto-create settings.toml, default profiles
- `src/terminal_ui.py` — QWidget architecture, search dialog, input handling
- `src/search_bar.py` — Rewrote as SearchDialog with correct PyQt6 API
- `OmniTerm.spec` — Dynamic winpty DLL detection
- `.github/workflows/ci.yml` — Nuitka build, installer, release automation

### Next Steps
1. **Test winpty with a minimal script** — verify PTY pipe connectivity
2. **Try conpty** — Windows 10 1809+ has built-in conpty, might work better
3. **Set sys.frozen manually** — add `sys.frozen = True` in Main.py for Nuitka builds
4. **Add splash screen** — show "Starting..." while PTY initializes
5. **Test on clean Windows install** — verify DLL dependencies
