"""
SSH session manager for OmniTerm.

Wraps paramiko to provide an SSH channel that behaves like a local PTY.
Supports password and key-based authentication, port forwarding, and
interactive shell sessions.
"""

from __future__ import annotations

import queue
import logging

log = logging.getLogger(__name__)


class SSHSession:
    """Manages an SSH connection with an interactive shell channel."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "",
        password: str | None = None,
        key_filename: str | None = None,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout

        self._client = None
        self._channel = None
        self.alive = False
        self.is_ready = False
        self.input_queue: queue.Queue[str | None] = queue.Queue()

    def connect(self) -> bool:
        """Establish the SSH connection and open an interactive shell.

        Returns True on success, False on failure.
        """
        try:
            import paramiko

            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs: dict = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": self.timeout,
            }
            if self.key_filename:
                connect_kwargs["key_filename"] = self.key_filename
            elif self.password:
                connect_kwargs["password"] = self.password

            self._client.connect(**connect_kwargs)

            # Open an interactive shell
            self._channel = self._client.invoke_shell(
                term="xterm-256color",
                width=120,
                height=40,
            )
            self._channel.settimeout(0.0)
            self.alive = True
            self.is_ready = True

            log.info("SSH connected to %s@%s:%d", self.username, self.host, self.port)
            return True

        except Exception as exc:
            log.error("SSH connection failed: %s", exc)
            self.alive = False
            self.is_ready = False
            return False

    def read(self, size: int = 4096) -> str | None:
        """Non-blocking read from the SSH channel."""
        if not self._channel or self._channel.closed:
            return None
        try:
            if self._channel.recv_ready():
                data = self._channel.recv(size)
                return data.decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    def write(self, data: str) -> None:
        """Send data to the SSH channel."""
        if self._channel and not self._channel.closed:
            try:
                self._channel.send(data)
            except Exception:
                pass

    def write_loop(self) -> None:
        """Background thread: dequeues input and sends to the channel."""
        while self.alive:
            try:
                data = self.input_queue.get(timeout=0.1)
                if data is None:
                    break
                self.write(data)
                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                break

    def resize(self, width: int, height: int) -> None:
        """Notify the SSH server of a terminal resize."""
        if self._channel and not self._channel.closed:
            try:
                self._channel.resize_pty(width=width, height=height)
            except Exception:
                pass

    def close(self) -> None:
        """Close the SSH connection and clean up."""
        self.alive = False
        self.is_ready = False
        self.input_queue.put(None)
        if self._channel:
            try:
                self._channel.close()
            except Exception:
                pass
            self._channel = None
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    @property
    def is_connected(self) -> bool:
        return (
            self.alive
            and self._channel is not None
            and not self._channel.closed
            and self._client is not None
        )
