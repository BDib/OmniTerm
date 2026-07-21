"""
Terminal engine — manages local PTY and SSH sessions.

Provides a unified interface for both local winpty processes and
remote SSH channels, with threaded I/O and Qt signal integration.
"""

import threading
import time
import queue
import logging
import traceback
import sys
import os

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)

# ── Error log helper ────────────────────────────────────────────────
_err_log = None


def _init_error_log():
    """Initialize the error log file (only when needed)."""
    global _err_log
    if _err_log is not None:
        return
    try:
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.getcwd()
        path = os.path.join(app_dir, "errors.txt")
        _err_log = open(path, "a", encoding="utf-8")
    except Exception:
        _err_log = None


def _elog(msg: str):
    """Write a message to errors.txt."""
    _init_error_log()
    if _err_log:
        try:
            _err_log.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            _err_log.flush()
        except Exception:
            pass
    log.error(msg)


def _elog_exc(msg: str, exc: Exception):
    """Write an exception with traceback to errors.txt."""
    _elog(f"{msg}: {exc}")
    _elog(traceback.format_exc())


class TerminalSignals(QObject):
    """Qt signals emitted from background threads."""
    text_ready = pyqtSignal(str)
    exited = pyqtSignal(str)


class TerminalEngine:
    """Manages a local PTY or SSH session with threaded I/O.

    Architecture:
        - **Reader thread** polls the source (PTY or SSH) and emits ``text_ready``.
        - **Writer thread** dequeues from ``input_queue`` and writes to the source.
        - Both threads exit when ``alive`` becomes ``False``.
    """

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
        self._elevated_mode = False
        self._elevated_proc = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self, cmd: str = "cmd.exe", admin: bool = False) -> bool:
        """Spawn a new local PTY running *cmd*.  Returns True on success."""
        self._cmd = cmd
        self.ssh = None
        self.serial = None
        _elog(f"Starting PTY: cmd={cmd!r}, admin={admin}")
        try:
            if admin:
                return self._start_elevated(cmd)

            from winpty import PtyProcess
            _elog(f"winpty imported OK, spawning {cmd!r}")
            self.pty = PtyProcess.spawn(cmd)
            _elog(f"PTY spawned, pid={getattr(self.pty, 'pid', '?')}")
            self.alive = True
            self.is_ready = False

            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True, name="pty-reader"
            )
            self._writer_thread = threading.Thread(
                target=self._write_loop, daemon=True, name="pty-writer"
            )
            self._reader_thread.start()
            self._writer_thread.start()
            _elog("PTY threads started")
            return True
        except ImportError as exc:
            _elog_exc("winpty import failed — DLL missing?", exc)
            self.alive = False
            self.is_ready = False
            self.signals.exited.emit(f"[ERROR: winpty not available: {exc}]")
            return False
        except FileNotFoundError as exc:
            _elog_exc(f"Shell not found: {cmd!r}", exc)
            self.alive = False
            self.is_ready = False
            self.signals.exited.emit(f"[ERROR: Command not found: {cmd}]")
            return False
        except Exception as exc:
            _elog_exc(f"Failed to spawn PTY: {cmd!r}", exc)
            self.alive = False
            self.is_ready = False
            self.signals.exited.emit(f"[ERROR: {exc}]")
            return False

    def _start_elevated(self, cmd: str) -> bool:
        """Launch *cmd* elevated with UAC prompt via ShellExecuteW."""
        import ctypes
        import shlex

        _elog(f"Starting elevated: {cmd!r}")
        try:
            parts = shlex.split(cmd)
            file = parts[0] if parts else cmd
            params = " ".join(parts[1:]) if len(parts) > 1 else ""

            _elog(f"ShellExecuteW: runas {file!r} {params!r}")
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", file, params, None, 1
            )
            _elog(f"ShellExecuteW returned {result}")
            if result <= 32:
                _elog(f"ShellExecuteW failed (result={result}) — UAC cancelled?")
                self.alive = False
                self.is_ready = False
                return False

            self.alive = True
            self.is_ready = True
            self._elevated_mode = True

            self._reader_thread = threading.Thread(
                target=self._elevated_wait_loop, daemon=True, name="elev-wait"
            )
            self._reader_thread.start()
            return True

        except Exception as exc:
            _elog_exc("Failed to start elevated process", exc)
            self.alive = False
            self.is_ready = False
            return False

    def _elevated_wait_loop(self) -> None:
        """Keep the tab alive while elevated process runs."""
        while self.alive:
            time.sleep(1)
        self.is_ready = False
        self.signals.exited.emit("[Admin session ended]")

    # ── Local PTY I/O threads ─────────────────────────────────────────

    def _read_loop(self) -> None:
        time.sleep(0.5)
        self.is_ready = True
        _elog("Reader thread started")

        while self.alive:
            try:
                if self.pty:
                    text = self.pty.read(1024)
                    if text:
                        if isinstance(text, bytes):
                            text = text.decode("utf-8", errors="replace")
                        self.signals.text_ready.emit(text)
            except EOFError:
                _elog("PTY reached EOF (process exited)")
                break
            except Exception as exc:
                _elog_exc("Reader thread error", exc)
                break
            time.sleep(0.01)

        self.alive = False
        self.is_ready = False
        _elog("Reader thread exiting")
        self.signals.exited.emit("[Process exited]")

    def _write_loop(self) -> None:
        _elog("Writer thread started")
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
                _elog_exc("Writer thread error", exc)
                break
        _elog("Writer thread exiting")

    # ── SSH I/O threads ───────────────────────────────────────────────

    def _ssh_read_loop(self) -> None:
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

    def _ssh_write_loop(self) -> None:
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

    # ── Serial I/O threads ─────────────────────────────────────────────

    def _serial_read_loop(self) -> None:
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

    def _serial_write_loop(self) -> None:
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

    # ── SSH session ────────────────────────────────────────────────────

    def start_ssh(self, host: str, port: int = 22, username: str = "",
                  password: str | None = None,
                  key_filename: str | None = None) -> bool:
        """Connect to a remote host via SSH. Returns True on success."""
        from ssh_session import SSHSession

        self.pty = None
        self.ssh = SSHSession(
            host=host, port=port, username=username,
            password=password, key_filename=key_filename,
        )

        if not self.ssh.connect():
            self.alive = False
            self.is_ready = False
            return False

        self.alive = True
        self.is_ready = True

        self._reader_thread = threading.Thread(
            target=self._ssh_read_loop, daemon=True, name="ssh-reader"
        )
        self._writer_thread = threading.Thread(
            target=self._ssh_write_loop, daemon=True, name="ssh-writer"
        )
        self._reader_thread.start()
        self._writer_thread.start()
        return True

    # ── Serial session ─────────────────────────────────────────────────

    def start_serial(self, port: str, baudrate: int = 115200,
                     bytesize: int = 8, parity: str = "N",
                     stopbits: float = 1) -> bool:
        """Open a serial port connection. Returns True on success."""
        from serial_session import SerialSession

        self.pty = None
        self.ssh = None
        self.serial = SerialSession(
            port=port, baudrate=baudrate, bytesize=bytesize,
            parity=parity, stopbits=stopbits,
        )

        if not self.serial.connect():
            self.alive = False
            self.is_ready = False
            return False

        self.alive = True
        self.is_ready = True

        self._reader_thread = threading.Thread(
            target=self._serial_read_loop, daemon=True, name="serial-reader"
        )
        self._writer_thread = threading.Thread(
            target=self._serial_write_loop, daemon=True, name="serial-writer"
        )
        self._reader_thread.start()
        self._writer_thread.start()
        return True

    # ── Restart / Kill ────────────────────────────────────────────────

    def restart(self) -> bool:
        """Kill the current session and spawn a fresh one."""
        self.kill()
        time.sleep(0.1)
        if self.ssh is not None:
            return False
        return self.start(self._cmd)

    def kill(self) -> None:
        """Terminate the session and stop both I/O threads."""
        self.alive = False
        self.is_ready = False
        self.input_queue.put(None)

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

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        if self.ssh:
            return self.alive and self.ssh.is_connected
        if self.serial:
            return self.alive and self.serial.is_connected
        if self._elevated_mode:
            return self.alive
        return self.alive and self.pty is not None and self.pty.isalive()

    @property
    def is_ssh(self) -> bool:
        return self.ssh is not None

    @property
    def is_serial(self) -> bool:
        return self.serial is not None

    # ── Public API ─────────────────────────────────────────────────────

    def write(self, data: str) -> None:
        """Enqueue *data* to be written to the terminal."""
        if self.alive:
            self.input_queue.put(data)

    def resize(self, width: int, height: int) -> None:
        """Notify the terminal of a resize (SSH only, no-op for local PTY)."""
        if self.ssh:
            self.ssh.resize(width, height)
