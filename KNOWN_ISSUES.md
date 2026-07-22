# Known Issues

## Current Limitations

### Terminal Emulation
- **Append-only output model** — QTextEdit is not a grid terminal. Cursor movement, line overwrite, and alternate screen buffer are not fully supported. Output is rendered linearly.
- **CR+line overwrite** — Shell line redraws may show duplicated text because CR is ignored for line endings to prevent prompt corruption.
- **PowerShell PSReadLine** — PSReadLine's live syntax highlighting uses cursor positioning that doesn't work perfectly in the append-only model. The `-NoProfile` flag is used to disable it.
- **Scrollback** — Scrollback buffer is implemented but not wired into the rendering pipeline.

### Input
- **Tab completion** — Tab is forwarded to the shell for completion, but the completion result may not render correctly due to cursor positioning limitations.

### Platform
- **Nuitka on CI** — Nuitka compilation fails on GitHub Actions due to MSVC linker issues with the CI environment. Nuitka builds are only available locally via `.\build.ps1`. GHA CI automatically builds PyInstaller releases instead.

### Profiles
- **Admin tabs** — Run As Admin opens a new elevated OmniTerm window (Windows security requirement). Admin tabs cannot run in the same non-elevated window.

### UI
- **Split panes** — Removed in v1.2.0 (didn't work with the QWidget-based terminal architecture).
- **Session persistence** — Open tabs/layout is not saved across sessions.
- **Font picker** — No GUI to select from installed monospace fonts (config only).
