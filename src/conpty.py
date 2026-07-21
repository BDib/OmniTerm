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
CREATE_NO_WINDOW = 0x08000000
INVALID_HANDLE_VALUE = wt.HANDLE(-1).value

k32 = ctypes.windll.kernel32


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
        except Exception as exc:
            self.alive = False
            return False

    def write(self, data: str) -> None:
        if self._alive and self._session and self._session.h_write:
            raw = data.encode("utf-8", errors="replace")
            written = wt.DWORD(0)
            k32.WriteConsoleInputCharacterW(self._session.h_write, raw, len(raw), ctypes.byref(written))

    def kill(self) -> None:
        self._alive = False
        s = self._session
        if s:
            if s.h_process:
                k32.TerminateProcess(s.h_process, 0)
            for h in (s.h_console, s.h_process, s.h_thread):
                if h:
                    k32.CloseHandle(h)
            self._session = None

    # ── Internals ───────────────────────────────────────────────────

    def _create_console(self, cmd: str, w: int, h: int) -> ConPTYSession:
        s = ConPTYSession()
        # Create pipes for the console
        h_con_in = wt.HANDLE()
        h_con_out = wt.HANDLE()
        k32.CreatePipe(ctypes.byref(h_con_in), ctypes.byref(h_con_out), None, 0)
        # Create pseudo console
        h_pc = wt.HANDLE()
        hr = k32.CreatePseudoConsole(
            wt._COORD(0, 0), h_con_in, h_con_out, 0, ctypes.byref(h_pc))
        if hr != 0:
            raise OSError(f"CreatePseudoConsole failed: 0x{hr:08x}")
        # Resize to requested dimensions
        k32.ResizePseudoConsole(h_pc, wt._COORD(w, h))
        s.h_console = h_pc
        # Build startup info with pseudo console
        si = wt.STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        si.dwFlags = STARTF_USESTDHANDLES
        attr_size = wt.DWORD(0)
        k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        attr_list = (ctypes.c_byte * attr_size.value)()
        k32.InitializeProcThreadAttributeList(ctypes.cast(attr_list, wt.LPVOID), 1, 0, ctypes.byref(attr_size))
        k32.UpdateProcThreadAttribute(
            ctypes.cast(attr_list, wt.LPVOID), 0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            h_pc, ctypes.sizeof(h_pc), None, None)
        si.lpAttributeList = ctypes.cast(attr_list, wt.LPVOID)
        # Create process
        pi = wt.PROCESS_INFORMATION()
        success = k32.CreateProcessW(
            None, cmd, None, None, False,
            EXTENDED_STARTUPINFO_PRESENT_FLAG | CREATE_NO_WINDOW,
            None, None, ctypes.byref(si), ctypes.byref(pi))
        if not success:
            raise OSError(f"CreateProcessW failed: {ctypes.GetLastError()}")
        s.h_process = pi.hProcess
        s.h_thread = pi.hThread
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
            else:
                time.sleep(0.01)
        self._alive = False
        self.exited.emit("[Process exited]")
