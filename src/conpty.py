"""ConPTY wrapper — Windows Pseudo Console API via ctypes.

ConPTY (available since Windows 10 1809) provides a proper PTY
without the limitations of winpty.  This module wraps the minimal
Win32 API surface needed to create a console, spawn a process, and
pipe I/O.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import os, sys, threading, time, queue
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal

# ── Win32 constants ────────────────────────────────────────────────
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT_FLAG = 0x00080000
STARTF_USESTDHANDLES = 0x00000100
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

k32 = ctypes.windll.kernel32


# ── STARTUPINFOEXW — extended startup info with attribute list ─────
# Python's ctypes.wintypes only has STARTUPINFOW (no lpAttributeList).
# We define STARTUPINFOEXW so CreateProcessW actually sees the attribute
# list that carries the ConPTY handle.

class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPWSTR),
        ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD),
        ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD),
        ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD),
        ("cbReserved2", wt.WORD),
        ("lpReserved2", wt.LPVOID),
        ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE),
        ("hStdError", wt.HANDLE),
    ]


class STARTUPINFOEXW(_STARTUPINFOW):
    _fields_ = [
        ("lpAttributeList", ctypes.c_void_p),
    ]


@dataclass
class ConPTYSession:
    """Holds handles for a single ConPTY session."""
    h_console: int = 0
    h_read: int = 0
    h_write: int = 0
    h_process: int = 0
    h_thread: int = 0


class ConPTYEngine(QObject):
    """ConPTY-backed terminal engine with Qt signals."""
    text_ready = pyqtSignal(str)
    exited = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._session: ConPTYSession | None = None
        self._alive = False
        self._reader: threading.Thread | None = None

    # ── Public API ─────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return self._alive

    def start(self, cmd: str = "cmd.exe", width: int = 120, height: int = 40) -> bool:
        """Spawn *cmd* inside a ConPTY.  Returns True on success."""
        try:
            self._session = self._create_console(cmd, width, height)
            self._alive = True
            self._reader = threading.Thread(target=self._read_loop, daemon=True, name="conpty-reader")
            self._reader.start()
            return True
        except Exception:
            self._alive = False
            return False

    def write(self, data: str) -> None:
        if self._alive and self._session and self._session.h_write:
            raw = data.encode("utf-8", errors="replace")
            written = wt.DWORD(0)
            k32.WriteFile(
                self._session.h_write, raw, len(raw),
                ctypes.byref(written), None,
            )

    def kill(self) -> None:
        self._alive = False
        s = self._session
        if s:
            if s.h_process:
                k32.TerminateProcess(s.h_process, 0)
            for h in (s.h_console, s.h_process, s.h_thread):
                if h:
                    k32.CloseHandle(h)
            # Close pipe ends
            if s.h_read:
                k32.CloseHandle(s.h_read)
            if s.h_write:
                k32.CloseHandle(s.h_write)
            self._session = None

    # ── Internals ───────────────────────────────────────────────────

    def _create_console(self, cmd: str, w: int, h: int) -> ConPTYSession:
        s = ConPTYSession()

        # Create pipes for the pseudo console.
        # h_con_in  = read end  (we read console output from this)
        # h_con_out = write end (we write user input to this)
        h_con_in = wt.HANDLE()
        h_con_out = wt.HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_con_in), ctypes.byref(h_con_out), None, 0):
            raise OSError(f"CreatePipe failed: {ctypes.GetLastError()}")

        # Create pseudo console
        h_pc = wt.HANDLE()
        hr = k32.CreatePseudoConsole(
            wt._COORD(0, 0), h_con_in, h_con_out, 0, ctypes.byref(h_pc))
        if hr != 0:
            k32.CloseHandle(h_con_in)
            k32.CloseHandle(h_con_out)
            raise OSError(f"CreatePseudoConsole failed: 0x{hr:08x}")

        # Resize to requested dimensions
        k32.ResizePseudoConsole(h_pc, wt._COORD(w, h))
        s.h_console = h_pc

        # Build attribute list with the pseudo console handle.
        # This MUST use STARTUPINFOEXW (not STARTUPINFOW) so that
        # CreateProcessW actually reads lpAttributeList from memory.
        attr_size = wt.DWORD(0)
        k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        attr_buf = (ctypes.c_byte * attr_size.value)()
        attr_ptr = ctypes.cast(attr_buf, ctypes.c_void_p)
        if not k32.InitializeProcThreadAttributeList(attr_ptr, 1, 0, ctypes.byref(attr_size)):
            raise OSError(f"InitializeProcThreadAttributeList failed: {ctypes.GetLastError()}")
        if not k32.UpdateProcThreadAttribute(
            attr_ptr, 0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            h_pc, ctypes.sizeof(h_pc), None, None):
            raise OSError(f"UpdateProcThreadAttribute failed: {ctypes.GetLastError()}")

        # Use STARTUPINFOEXW so cb and lpAttributeList are both correct
        si = STARTUPINFOEXW()
        si.cb = ctypes.sizeof(si)
        si.dwFlags = STARTF_USESTDHANDLES
        si.lpAttributeList = attr_ptr

        # Create process — no CREATE_NO_WINDOW; ConPTY owns the console
        pi = wt.PROCESS_INFORMATION()
        if not k32.CreateProcessW(
            None, cmd, None, None, False,
            EXTENDED_STARTUPINFO_PRESENT_FLAG,
            None, None, ctypes.byref(si), ctypes.byref(pi)):
            err = ctypes.GetLastError()
            k32.DeleteProcThreadAttributeList(attr_ptr)
            raise OSError(f"CreateProcessW failed: {err}")

        s.h_process = pi.hProcess
        s.h_thread = pi.hThread
        # Pipe mapping:
        #   Console reads from h_con_in  → we write to h_con_out to send input
        #   Console writes to h_con_out  → we read from h_con_in to get output
        s.h_read = h_con_in
        s.h_write = h_con_out
        return s

    def _read_loop(self) -> None:
        s = self._session
        buf = (ctypes.c_char * 4096)()
        read = wt.DWORD(0)
        time.sleep(0.3)
        while self._alive:
            ok = k32.ReadFile(s.h_read, buf, len(buf), ctypes.byref(read), None)
            if ok and read.value > 0:
                chunk = buf[:read.value].decode("utf-8", errors="replace")
                self.text_ready.emit(chunk)
            elif not ok:
                # Pipe closed or error — process likely exited
                break
            else:
                time.sleep(0.01)
        self._alive = False
        self.exited.emit("[Process exited]")
