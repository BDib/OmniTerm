"""ConPTY wrapper — Windows Pseudo Console API via ctypes.

Uses TWO separate pipes: one for input (host → shell) and one for
output (shell → host), preventing echo feedback loops.
Uses OVERLAPPED I/O for the read pipe so we can cancel pending reads
from kill() — synchronous ReadFile cannot be cancelled from another thread.
"""
from __future__ import annotations
import ctypes
import ctypes.wintypes as wt
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from PyQt6.QtCore import QObject, pyqtSignal

PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
EXTENDED_STARTUPINFO_PRESENT_FLAG = 0x00080000
STARTF_USESTDHANDLES = 0x00000100
ERROR_OPERATION_ABORTED = 995
ERROR_IO_INCOMPLETE = 996
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 0x102
INFINITE = 0xFFFFFFFF

k32 = ctypes.windll.kernel32


def _elog(msg: str):
    try:
        d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
        with open(os.path.join(d, "errors.txt"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
        ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD),
        ("dwFillAttribute", wt.DWORD), ("dwFlags", wt.DWORD),
        ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", wt.LPVOID), ("hStdInput", wt.HANDLE),
        ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]

class STARTUPINFOEXW(_STARTUPINFOW):
    _fields_ = [("lpAttributeList", ctypes.c_void_p)]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
        ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD),
    ]

class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_ulong),
        ("InternalHigh", ctypes.c_ulong),
        ("Offset", wt.DWORD),
        ("OffsetHigh", wt.DWORD),
        ("hEvent", wt.HANDLE),
    ]

@dataclass
class ConPTYSession:
    h_console: int = 0
    h_read: int = 0
    h_write: int = 0
    h_process: int = 0
    h_thread: int = 0
    read_event: int = 0  # event for overlapped read cancellation


class ConPTYEngine(QObject):
    text_ready = pyqtSignal(str)
    exited = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._session: ConPTYSession | None = None
        self._alive = False
        self._killed = False
        self._reader: threading.Thread | None = None

    @property
    def alive(self) -> bool:
        return self._alive

    def start(self, cmd: str = "cmd.exe", width: int = 120, height: int = 40, cwd: str | None = None) -> bool:
        try:
            self._session = self._create_console(cmd, width, height, cwd)
            self._alive = True
            self._killed = False
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
            try:
                raw = data.encode("utf-8", errors="replace")
                written = wt.DWORD(0)
                k32.WriteFile(self._session.h_write, raw, len(raw), ctypes.byref(written), None)
            except Exception:
                pass

    def kill(self) -> None:
        if self._killed:
            return
        self._killed = True
        self._alive = False
        s = self._session
        self._session = None
        if not s:
            return

        # 1. Terminate the child process
        if s.h_process:
            try:
                k32.TerminateProcess(s.h_process, 0)
            except Exception:
                pass
            # Wait briefly for process to actually exit
            k32.WaitForSingleObject(s.h_process, 500)

        # 2. Cancel any pending overlapped ReadFile — this unblocks the reader thread
        if s.h_read and s.read_event:
            try:
                k32.CancelIoEx(s.h_read, None)
            except Exception:
                pass
            # Signal the event so WaitForSingleObject returns
            try:
                k32.SetEvent(s.read_event)
            except Exception:
                pass

        # 3. Close the read event
        if s.read_event:
            try:
                k32.CloseHandle(s.read_event)
            except Exception:
                pass

        # 4. Close pipe handles
        for h in (s.h_read, s.h_write):
            if h:
                try:
                    k32.CloseHandle(h)
                except Exception:
                    pass

        # 5. Close pseudo console — releases conhost.exe
        if s.h_console:
            try:
                k32.ClosePseudoConsole(s.h_console)
            except (AttributeError, Exception):
                pass

        # 6. Close process/thread handles
        for h in (s.h_process, s.h_thread):
            if h:
                try:
                    k32.CloseHandle(h)
                except Exception:
                    pass

        # 7. Wait for reader thread to finish (with timeout)
        if self._reader and self._reader.is_alive():
            self._reader.join(timeout=2.0)

    def _create_console(self, cmd: str, w: int, h: int, cwd: str | None = None) -> ConPTYSession:
        s = ConPTYSession()

        h_in_read = wt.HANDLE()
        h_in_write = wt.HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_in_read), ctypes.byref(h_in_write), None, 0):
            raise OSError(f"CreatePipe (input) failed: {ctypes.GetLastError()}")

        h_out_read = wt.HANDLE()
        h_out_write = wt.HANDLE()
        if not k32.CreatePipe(ctypes.byref(h_out_read), ctypes.byref(h_out_write), None, 0):
            k32.CloseHandle(h_in_read)
            k32.CloseHandle(h_in_write)
            raise OSError(f"CreatePipe (output) failed: {ctypes.GetLastError()}")

        h_pc = wt.HANDLE()
        hr = k32.CreatePseudoConsole(
            wt._COORD(w, h), h_in_read, h_out_write, 0, ctypes.byref(h_pc))
        if hr != 0:
            for h in (h_in_read, h_in_write, h_out_read, h_out_write):
                k32.CloseHandle(h)
            raise OSError(f"CreatePseudoConsole failed: 0x{hr & 0xFFFFFFFF:08x}")
        s.h_console = h_pc

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

        k32.DeleteProcThreadAttributeList(attr_ptr)

        s.h_process = pi.hProcess
        s.h_thread = pi.hThread
        s.h_read = h_out_read
        s.h_write = h_in_write

        k32.CloseHandle(h_in_read)
        k32.CloseHandle(h_out_write)

        # Create an event for overlapped reads — lets us cancel pending I/O
        read_event = k32.CreateEventW(None, True, False, None)
        s.read_event = read_event if read_event else 0

        return s

    def _read_loop(self) -> None:
        s = self._session
        if not s:
            return
        buf = (ctypes.c_char * 4096)()
        overlapped = OVERLAPPED()
        if s.read_event:
            overlapped.hEvent = s.read_event
        read = wt.DWORD(0)
        STILL_ACTIVE = 259
        time.sleep(0.3)
        while self._alive:
            try:
                # Reset the event before each read
                if s.read_event:
                    k32.ResetEvent(s.read_event)
                # Overlapped read — we wait on the event so we can cancel
                ok = k32.ReadFile(s.h_read, buf, len(buf), ctypes.byref(read), ctypes.byref(overlapped))
                if ok:
                    # Read completed immediately
                    if read.value > 0:
                        chunk = buf[:read.value].decode("utf-8", errors="replace")
                        self.text_ready.emit(chunk)
                    else:
                        break
                else:
                    err = ctypes.GetLastError()
                    if err == 997:  # ERROR_IO_PENDING — wait for completion
                        wait_rc = k32.WaitForSingleObject(s.read_event, 200)
                        if wait_rc == WAIT_OBJECT_0:
                            # Read completed — get result
                            transferred = wt.DWORD(0)
                            k32.GetOverlappedResult(s.h_read, ctypes.byref(overlapped), ctypes.byref(transferred), False)
                            if transferred.value > 0:
                                chunk = buf[:transferred.value].decode("utf-8", errors="replace")
                                self.text_ready.emit(chunk)
                            else:
                                break
                        elif wait_rc == WAIT_TIMEOUT:
                            # Timed out — check if we should still be alive
                            continue
                        else:
                            # Abandoned or error — exit
                            break
                    elif err == ERROR_OPERATION_ABORTED:
                        # Cancelled by kill() — exit
                        break
                    elif err == 109:  # ERROR_BROKEN_PIPE
                        break
                    else:
                        break
            except Exception:
                break
            # Safety net: check if process exited
            if s.h_process:
                exit_code = wt.DWORD(0)
                if k32.GetExitCodeProcess(s.h_process, ctypes.byref(exit_code)):
                    if exit_code.value != STILL_ACTIVE:
                        break
        self._alive = False
        self.exited.emit("[Process exited]")
