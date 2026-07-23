# Known Issues & Fixes — Session Log

## All Critical Issues Resolved (v2.5.1)

### Fix History

| Version | Issue | Root Cause | Fix |
|---------|-------|------------|-----|
| v2.5.1 | `exit` command doesn't close tab | `kill()` didn't close pipe handles; `ReadFile` blocked forever | Close pipe handles in `kill()`, add `GetExitCodeProcess` safety net |
| v2.5.0 | Close/X unreliable, search methods crash | `_closing` guard blocked tab cleanup; `_search_next` referenced non-existent `self._tabs` | Remove `_closing` guard, fix search methods to use parent MainWindow |
| v2.4.4 | Exit command not closing tab (partial) | `ReadFile` EOF detection incomplete | Break on both `not ok` and `read.value == 0` |
| v2.4.3 | Exit/close crash | Closing pipe while `ReadFile` blocks | Remove pipe close from `kill()`, add `GetExitCodeProcess` check |
| v2.1.0 | cmd.exe exits after 5 seconds (Nuitka) | STARTUPINFOW used instead of STARTUPINFOEXW | Defined proper STARTUPINFOEXW ctypes Structure |
| v2.1.1 | ConPTY shell not launching | CreateProcessW needs writable buffer | Use ctypes.create_unicode_buffer(cmd) |
| v2.1.2 | CreatePseudoConsole E_INVALIDARG | COORD(0,0) is invalid | Pass actual dimensions (w,h) |
| v2.1.3 | Missing PROCESS_INFORMATION | ctypes.wintypes has no PROCESS_INFORMATION | Define as ctypes Structure |
| v2.1.4 | Input not reaching shell | ConPTY has no writer thread | write() calls _conpty.write() directly |
| v2.1.5 | Echo feedback loop (junk files) | Single pipe for I/O | Use TWO separate pipes |
| v2.1.6 | Arrow keys echo VT sequences | VT sequences echoed by cmd.exe | Don't forward arrow keys, let QTextEdit handle |

### Current Architecture
- ConPTY with two separate pipes (input + output)
- `kill()` closes ALL handles (process, thread, console, AND pipes) to unblock `_read_loop`
- `_read_loop` checks `GetExitCodeProcess` as safety net for stale pipe reads
- Direct write path (no queue for ConPTY)
- Arrow keys handled by QTextEdit (cmd.exe handles its own line editing)
- Tab forwarded to shell for completion
- Comprehensive error logging to errors.txt

### Build Verified
- Python interpreter: Working
- PyInstaller: Working (48.8 MB)
- Nuitka: Working (32.2 MB)
- 142 tests passing
