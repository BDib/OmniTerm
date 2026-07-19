"""
Terminal engine — manages local PTY and SSH sessions.

Provides a unified interface for both local winpty processes and
remote SSH channels, with threaded I/O and Qt signal integration.
"""

import threading
import time
import queue
import logging

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)


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

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self, cmd: str = "cmd.exe") -> bool:
        """Spawn a new local PTY running *cmd*.  Returns True on success."""
        self._cmd = cmd
        self.ssh = None
        try:
            from winpty import PtyProcess
            self.pty = PtyProcess.spawn(cmd)
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
            return True
        except Exception as exc:
            log.error("Failed to spawn PTY: %s", exc)
            self.alive = False
            self.is_ready = False
            return False

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

    def restart(self) -> bool:
        """Kill the current session and spawn a fresh one."""
        self.kill()
        time.sleep(0.1)
        if self.ssh is not None:
            # Can't restart SSH without re-connecting
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

    @property
    def is_alive(self) -> bool:
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

    # ── Local PTY I/O threads ─────────────────────────────────────────

    def _read_loop(self) -> None:
        time.sleep(0.5)
        self.is_ready = True

        while self.alive:
            try:
                if self.pty:
                    text = self.pty.read(1024)
                    if text:
                        if isinstance(text, bytes):
                            text = text.decode("utf-8", errors="replace")
                        self.signals.text_ready.emit(text)
            except EOFError:
                break
            except Exception:
                break
            time.sleep(0.01)

        self.alive = False
        self.is_ready = False
        self.signals.exited.emit("[Process exited]")

    def _write_loop(self) -> None:
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
            except Exception:
                break

    # ── SSH I/O threads ───────────────────────────────────────────────

    def _ssh_read_loop(self) -> None:
        while self.alive and self.ssh:
            try:
                text = self.ssh.read(4096)
                if text:
                    self.signals.text_ready.emit(text)
                time.sleep(0.01)
            except Exception:
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
            except Exception:
                break

    # ── Serial I/O threads ─────────────────────────────────────────────

    def _serial_read_loop(self) -> None:
        while self.alive and self.serial:
            try:
                text = self.serial.read(4096)
                if text:
                    self.signals.text_ready.emit(text)
                time.sleep(0.01)
            except Exception:
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
            except Exception:
                break

    # ── Public API ─────────────────────────────────────────────────────

    def write(self, data: str) -> None:
        """Enqueue *data* to be written to the terminal."""
        if self.alive:
            self.input_queue.put(data)

    def resize(self, width: int, height: int) -> None:
        """Notify the terminal of a resize (SSH only, no-op for local PTY)."""
        if self.ssh:
            self.ssh.resize(width, height)
