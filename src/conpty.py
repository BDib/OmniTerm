"""ConPTY wrapper — Windows Pseudo Console API via ctypes.

ConPTY (available since Windows 10 1809) provides a proper PTY
without the limitations of winpty.  This module wraps the minimal
Win32 API surface needed to create a console, spawn a process, and
pipe I/O.

Uses TWO separate pipes: one for input (host → shell) and one for
output (shell → host), preventing echo feedback loops.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import os, sys, threading, time, traceback
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

# ── Win32 constants ────────────────────────────────────────────────
PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT_FLAG = 0x00080000
STARTF_USESTDHANDLES = 0x00000100

k32 = ctypes.windll.kernel32


def _elog(msg: str):
    try:
        d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
        with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


# ── Win32 structs ─────────────────────────────────────────────────

class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("lpReserved", wt.LPWSTR),
        ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR),
        ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD),
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
    _fields_ = [("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD),
    ]


@dataclass
class ConPTYSession:
    h_console: int = 0
    h_read: int = 0       # host reads shell output from this
    h_write: int = 0      # host writes user input to this
    h_process: int = 0
    h_thread: int = 0


class ConPTYEngine(QObject):
    text_ready = pyqtSignal(str)
    exited = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._session: ConPTYSession | None = None
        self._alive = False
        self._reader: threading.Thread | None = None

    @property
    def alive(self) -> bool:
        return self._alive

    def start(self, cmd: str = "cmd.exe", width: int = 120, height: int = 40, cwd: str | None = None) -> bool:
        try:
            self._session = self._create_console(cmd, width, height, cwd)
            self._alive = True
            self._reader = threading.Thread(target=self._read_loop, daemon=True, name="conpty-reader")
            self._reader.start()
            _elog("ConPTY start: success")
            return True
        except Exception as exc:
            _elog(f"ConPTY start FAILED: {exc}")
            _elog(traceback.format_exc())
            self._alive = False
            return False

    def write(self, data: str) -> None:
        if self._alive and self._session and self._session.h_write:
            raw = data.encode("utf-8", errors="replace")
            written = wt.DWORD(0)
            k32.WriteFile(self._session.h_write, raw, len(raw), ctypes.byref(written), None)

    def kill(self) -> None:
        self._alive = False
        s = self._session
        if s:
            if s.h_process:
                k32.TerminateProcess(s.h_process, 0)
            for h in (s.h_console, s.h_process, s.h_thread, s.h_read, s.h_write):
                if h:
                    k32.CloseHandle(h)
            self._session = None

    def _create_console(self, cmd: str, w: int, h: int, cwd: str | None = None) -> ConPTYSession:
        s = ConPTYSession()

        # ── Pipe 1: host → shell (input) ──────────────────────────
        # h_in_read  = read end  (passed to ConPTY as hInput)
        # h_in_write = write end (host writes user input here)
        h_in_read = wt.HANDLE()
        h_in_write = wt.HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_in_read), ctypes.byref(h_in_write), None, 0):
            raise OSError(f"CreatePipe (input) failed: {ctypes.GetLastError()}")

        # ── Pipe 2: shell → host (output) ─────────────────────────
        # h_out_read  = read end  (host reads shell output from here)
        # h_out_write = write end (passed to ConPTY as hOutput)
        h_out_read = wt.HANDLE()
        h_out_write = wt.HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_out_read), ctypes.byref(h_out_write), None, 0):
            k32.CloseHandle(h_in_read)
            k32.CloseHandle(h_in_write)
            raise OSError(f"CreatePipe (output) failed: {ctypes.GetLastError()}")

        _elog(f"Pipes OK: in_read={h_in_read.value} in_write={h_in_write.value} "
              f"out_read={h_out_read.value} out_write={h_out_write.value}")

        # ── Create pseudo console ──────────────────────────────────
        h_pc = wt.HANDLE()
        hr = k32.CreatePseudoConsole(
            wt._COORD(w, h), h_in_read, h_out_write, 0, ctypes.byref(h_pc))
        if hr != 0:
            for h in (h_in_read, h_in_write, h_out_read, h_out_write):
                k32.CloseHandle(h)
            raise OSError(f"CreatePseudoConsole failed: 0x{hr & 0xFFFFFFFF:08x}")
        _elog(f"CreatePseudoConsole OK: h_pc={h_pc.value}")
        s.h_console = h_pc

        # ── Build attribute list ───────────────────────────────────
        attr_size = wt.DWORD(0)
        k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(attr_size))
        attr_buf = (ctypes.c_byte * attr_size.value)()
        attr_ptr = ctypes.cast(attr_buf, ctypes.c_void_p)
        if not k32.InitializeProcThreadAttributeList(attr_ptr, 1, 0, ctypes.byref(attr_size)):
            raise OSError(f"InitializeProcThreadAttributeList failed: {ctypes.GetLastError()}")
        if not k32.UpdateProcThreadAttribute(
            attr_ptr, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            h_pc, ctypes.sizeof(h_pc), None, None):
            raise OSError(f"UpdateProcThreadAttribute failed: {ctypes.GetLastError()}")

        # ── Create process ─────────────────────────────────────────
        si = STARTUPINFOEXW()
        si.cb = ctypes.sizeof(si)
        si.dwFlags = STARTF_USESTDHANDLES
        si.lpAttributeList = attr_ptr

        pi = PROCESS_INFORMATION()
        cmd_buf = ctypes.create_unicode_buffer(cmd)
        cwd_buf = ctypes.create_unicode_buffer(cwd) if cwd else None
        if not k32.CreateProcessW(
            None, cmd_buf, None, None, False,
            EXTENDED_STARTUPINFO_PRESENT_FLAG,
            None, cwd_buf, ctypes.byref(si), ctypes.byref(pi)):
            err = ctypes.GetLastError()
            k32.DeleteProcThreadAttributeList(attr_ptr)
            raise OSError(f"CreateProcessW failed: error={err}")
        _elog(f"CreateProcessW OK: pid={pi.dwProcessId}")

        k32.DeleteProcThreadAttributeList(attr_ptr)

        s.h_process = pi.hProcess
        s.h_thread = pi.hThread
        s.h_read = h_out_read      # host reads shell output from here
        s.h_write = h_in_write     # host writes user input to here

        # Close the ends that the host doesn't use
        k32.CloseHandle(h_in_read)   # ConPTY owns this end
        k32.CloseHandle(h_out_write) # ConPTY owns this end

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
                break
            else:
                time.sleep(0.01)
        self._alive = False
        self.exited.emit("[Process exited]")
