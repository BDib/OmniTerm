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
        self._conpty = None
        self._unix_pty = None

    def start(self, cmd: str = "cmd.exe", admin: bool = False, cwd: str | None = None) -> bool:
        self._cmd = cmd
        self.ssh = None
        self.serial = None
        _elog(f"Starting: cmd={cmd!r}, admin={admin}, cwd={cwd!r}")
        if os.name != "nt":
            return self._start_unix_pty(cmd, cwd)
        if admin:
            return self._start_elevated(cmd)
        return self._start_conpty(cmd, cwd)

    def _start_conpty(self, cmd: str, cwd: str | None = None) -> bool:
        """Start a ConPTY session."""
        try:
            from conpty import ConPTYEngine
            self._conpty = ConPTYEngine()
            if not self._conpty.start(cmd, cwd=cwd):
                _elog("ConPTYEngine.start() returned False")
                return False
            self.alive = True
            self.is_ready = True
            self._conpty.text_ready.connect(self.signals.text_ready.emit)
            self._conpty.exited.connect(self._on_conpty_exit)
            _elog("ConPTY started OK")
            return True
        except Exception as exc:
            _elog_exc("ConPTY failed", exc)
            return False

    def _start_unix_pty(self, cmd: str, cwd: str | None = None) -> bool:
        """Start a Unix PTY session."""
        try:
            from unix_pty import UnixPTYEngine
            self._unix_pty = UnixPTYEngine(self.signals)
            if not self._unix_pty.start(cmd, cwd=cwd):
                _elog("UnixPTYEngine.start() returned False")
                return False
            self.alive = True
            self.is_ready = True
            _elog("Unix PTY started OK")
            return True
        except Exception as exc:
            _elog_exc("Unix PTY failed", exc)
            return False

    def _on_conpty_exit(self, msg: str):
        _elog(f"ConPTY exit: {msg}")
        self.alive = False
        self.is_ready = False
        self.signals.exited.emit(msg)

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
        if not self.alive and not self._conpty and not self._unix_pty:
            return
        self.alive = False
        self.is_ready = False
        self.input_queue.put(None)
        if self._conpty:
            self._conpty.kill()
            self._conpty = None
        if self._unix_pty:
            self._unix_pty.kill()
            self._unix_pty = None
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
        if self._conpty:
            return self._conpty.alive
        if self._unix_pty:
            return self._unix_pty.alive
        if self.ssh:
            return self.alive and self.ssh.is_connected
        if self.serial:
            return self.alive and self.serial.is_connected
        return self.alive

    @property
    def is_ssh(self) -> bool:
        return self.ssh is not None

    @property
    def is_serial(self) -> bool:
        return self.serial is not None

    def write(self, data: str) -> None:
        if self.alive:
            if self._conpty:
                self._conpty.write(data)
            elif self._unix_pty:
                self._unix_pty.write(data)
            else:
                self.input_queue.put(data)

    def resize(self, width: int, height: int) -> None:
        if self.ssh:
            self.ssh.resize(width, height)
