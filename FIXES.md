# Known Issues & Fixes — Session Log

## All Critical Issues Resolved (v2.1.6)

### Fix History

| Version | Issue | Root Cause | Fix |
|---------|-------|------------|-----|
| v2.1.0 | cmd.exe exits after 5 seconds (Nuitka) | STARTUPINFOW used instead of STARTUPINFOEXW | Defined proper STARTUPINFOEXW ctypes Structure |
| v2.1.1 | ConPTY shell not launching | CreateProcessW needs writable buffer | Use ctypes.create_unicode_buffer(cmd) |
| v2.1.2 | CreatePseudoConsole E_INVALIDARG | COORD(0,0) is invalid | Pass actual dimensions (w,h) |
| v2.1.3 | Missing PROCESS_INFORMATION | ctypes.wintypes has no PROCESS_INFORMATION | Define as ctypes Structure |
| v2.1.4 | Input not reaching shell | ConPTY has no writer thread | write() calls _conpty.write() directly |
| v2.1.5 | Echo feedback loop (junk files) | Single pipe for I/O | Use TWO separate pipes |
| v2.1.6 | Arrow keys echo VT sequences | VT sequences echoed by cmd.exe | Don't forward arrow keys, let QTextEdit handle |

### Current Architecture
- ConPTY with two separate pipes (input + output)
- Direct write path (no queue for ConPTY)
- Arrow keys handled by QTextEdit (cmd.exe handles its own line editing)
- Tab forwarded to shell for completion
- Comprehensive error logging to errors.txt

### Build Verified
- Python interpreter: Working
- PyInstaller: Working
- Nuitka: Working
- 143 tests passing
