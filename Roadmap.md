# OmniTerm Roadmap

## Current Status — v2.5.4

Stable release with ConPTY backend, cross-platform builds (6 platforms), unified terminal screen, Arabic/bidi support, and 145 tests passing.

---

## Future Ideas

| Feature | Description |
|---------|-------------|
| Session Recording | Record terminal sessions to `.cast` files (asciinema-compatible) |
| Plugin API | Python plugin system for custom extensions |
| GPU Acceleration | Migrate rendering to QOpenGLWidget for massive output |
| Font Picker | Enumerate installed monospace fonts and let user pick |
| Quake Mode | `Ctrl+~` dropdown terminal (like console/tilda on Linux) |
| Tab Splits | Reimplement split panes with QWidget-based rendering |
| Custom Prompts | Per-profile custom prompt configuration |
| Tab Rename | Right-click tab to rename |
| Session Persistence | Save/restore open tabs across launches |
| Auto-Update | Check GitHub releases for new versions on startup |
