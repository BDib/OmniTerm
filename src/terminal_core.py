"""Terminal engine — manages local PTY and SSH sessions."""
from __future__ import annotations
import threading, time, queue, logging, traceback, sys, os
from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)
_err_log = None

def _elog(msg: str):
    global _err_log
    if _err_log is None:
        try:
            d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
            _err_log = open(os.path.join(d, "errors.txt"), "a", encoding="utf-8")
        except Exception:
            return
    try:
        _err_log.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        _err_log.flush()
    except Exception:
        pass

def _elog_exc(msg: str, exc: Exception):
    _elog(f"{msg}: {exc}")
    _elog(traceback.format_exc())


class TerminalSignals(QObject):
    text_ready = pyqtSignal(str)
    exited = pyqtSignal(str)


class TerminalEngine:
    """Manages a local PTY or SSH session with threaded I/O."""

    def __init__(self):
        self.signals = TerminalSignals()
        self.pty = None
        self.ssh = None
        self.serial = None
        self.alive = False
        self.is_ready = False
        self.input_queue: queue.Queue[str | None] = queue.Queue()
        self._cmd = "cmd.exe"
        self._reader_thread: threading.Thread | None = None
        self._writer_thread: threading.Thread | None = None
        self._backend: str = "none"  # "conpty", "winpty", "pipe"

    def start(self, cmd: str = "cmd.exe", admin: bool = False) -> bool:
        self._cmd = cmd
        self.ssh = None
        self.serial = None
        _elog(f"Starting: cmd={cmd!r}, admin={admin}")
        if admin:
            return self._start_elevated(cmd)
        # Try ConPTY first, fall back to winpty
        for backend_name, launcher in [("conpty", self._start_conpty), ("winpty", self._start_winpty)]:
            try:
                if launcher(cmd):
                    self._backend = backend_name
                    _elog(f"Using backend: {backend_name}")
                    return True
            except Exception as exc:
                _elog(f"{backend_name} failed: {exc}")
        _elog("All backends failed")
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit("[ERROR: No PTY backend available]")
        return False

    def _start_conpty(self, cmd: str) -> bool:
        """Try ConPTY via ctypes."""
        try:
            from conpty import ConPTYEngine
            self._conpty = ConPTYEngine()
            if not self._conpty.start(cmd):
                return False
            self.alive = True
            self.is_ready = True
            self._conpty.text_ready.connect(self.signals.text_ready.emit)
            self._conpty.exited.connect(self._on_conpty_exit)
            return True
        except Exception as exc:
            _elog(f"ConPTY error: {exc}")
            return False

    def _on_conpty_exit(self, msg: str):
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit(msg)

    def _start_winpty(self, cmd: str) -> bool:
        """Fall back to winpty."""
        from winpty import PtyProcess
        self.pty = PtyProcess.spawn(cmd)
        self.alive = True
        self.is_ready = False
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True, name="pty-reader")
        self._writer_thread = threading.Thread(target=self._write_loop, daemon=True, name="pty-writer")
        self._reader_thread.start()
        self._writer_thread.start()
        return True

    def _start_elevated(self, cmd: str) -> bool:
        import ctypes, shlex
        _elog(f"Starting elevated: {cmd!r}")
        try:
            parts = shlex.split(cmd)
            file = parts[0] if parts else cmd
            params = " ".join(parts[1:]) if len(parts) > 1 else ""
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", file, params, None, 1)
            if result <= 32:
                _elog(f"ShellExecuteW failed: {result}")
                return False
            self.alive = True
            self.is_ready = True
            threading.Thread(target=self._elevated_wait, daemon=True).start()
            return True
        except Exception as exc:
            _elog_exc("Elevated start failed", exc)
            return False

    def _elevated_wait(self):
        while self.alive:
            time.sleep(1)
        self.is_ready = False
        self.signals.exited.emit("[Admin session ended]")

    def _read_loop(self):
        time.sleep(0.5)
        self.is_ready = True
        _elog("Reader started")
        while self.alive:
            try:
                if self.pty:
                    text = self.pty.read(1024)
                    if text:
                        if isinstance(text, bytes):
                            text = text.decode("utf-8", errors="replace")
                        self.signals.text_ready.emit(text)
            except EOFError:
                _elog("PTY EOF")
                break
            except Exception as exc:
                _elog_exc("Reader error", exc)
                break
            time.sleep(0.01)
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit("[Process exited]")

    def _write_loop(self):
        while self.alive:
            try:
                data = self.input_queue.get(timeout=0.1)
                if data is None:
                    break
                if self.pty and self.alive:
                    self.pty.write(data)
                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception as exc:
                _elog_exc("Writer error", exc)
                break

    def start_ssh(self, host: str, port: int = 22, username: str = "",
                  password: str | None = None, key_filename: str | None = None) -> bool:
        from ssh_session import SSHSession
        self.pty = None
        self.ssh = SSHSession(host=host, port=port, username=username,
                              password=password, key_filename=key_filename)
        if not self.ssh.connect():
            self.alive = False
            self.is_ready = False
            return False
        self.alive = True
        self.is_ready = True
        self._reader_thread = threading.Thread(target=self._ssh_read_loop, daemon=True)
        self._writer_thread = threading.Thread(target=self._ssh_write_loop, daemon=True)
        self._reader_thread.start()
        self._writer_thread.start()
        return True

    def _ssh_read_loop(self):
        while self.alive and self.ssh:
            try:
                text = self.ssh.read(4096)
                if text:
                    self.signals.text_ready.emit(text)
                time.sleep(0.01)
            except Exception as exc:
                _elog_exc("SSH reader error", exc)
                break
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit("[SSH session ended]")

    def _ssh_write_loop(self):
        while self.alive:
            try:
                data = self.input_queue.get(timeout=0.1)
                if data is None:
                    break
                if self.ssh and self.alive:
                    self.ssh.write(data)
                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception as exc:
                _elog_exc("SSH writer error", exc)
                break

    def start_serial(self, port: str, baudrate: int = 115200, bytesize: int = 8,
                     parity: str = "N", stopbits: float = 1) -> bool:
        from serial_session import SerialSession
        self.pty = None
        self.ssh = None
        self.serial = SerialSession(port=port, baudrate=baudrate, bytesize=bytesize,
                                    parity=parity, stopbits=stopbits)
        if not self.serial.connect():
            self.alive = False
            self.is_ready = False
            return False
        self.alive = True
        self.is_ready = True
        self._reader_thread = threading.Thread(target=self._serial_read_loop, daemon=True)
        self._writer_thread = threading.Thread(target=self._serial_write_loop, daemon=True)
        self._reader_thread.start()
        self._writer_thread.start()
        return True

    def _serial_read_loop(self):
        while self.alive and self.serial:
            try:
                text = self.serial.read(4096)
                if text:
                    self.signals.text_ready.emit(text)
                time.sleep(0.01)
            except Exception as exc:
                _elog_exc("Serial reader error", exc)
                break
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit("[Serial connection closed]")

    def _serial_write_loop(self):
        while self.alive:
            try:
                data = self.input_queue.get(timeout=0.1)
                if data is None:
                    break
                if self.serial and self.alive:
                    self.serial.write(data)
                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception as exc:
                _elog_exc("Serial writer error", exc)
                break

    def kill(self) -> None:
        self.alive = False
        self.is_ready = False
        self.input_queue.put(None)
        if hasattr(self, "_conpty") and self._conpty:
            self._conpty.kill()
        if self.pty:
            try:
                self.pty.terminate()
                self.pty.close()
            except Exception:
                pass
            self.pty = None
        if self.ssh:
            try:
                self.ssh.close()
            except Exception:
                pass
            self.ssh = None
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
            self.serial = None

    @property
    def is_alive(self) -> bool:
        if hasattr(self, "_conpty") and self._conpty:
            return self._conpty.alive
        if self.ssh:
            return self.alive and self.ssh.is_connected
        if self.serial:
            return self.alive and self.serial.is_connected
        return self.alive and self.pty is not None and self.pty.isalive()

    @property
    def is_ssh(self) -> bool:
        return self.ssh is not None

    @property
    def is_serial(self) -> bool:
        return self.serial is not None

    def write(self, data: str) -> None:
        if self.alive:
            self.input_queue.put(data)

    def resize(self, width: int, height: int) -> None:
        if self.ssh:
            self.ssh.resize(width, height)
