"""
Serial console manager for OmniTerm.

Wraps pyserial to provide a serial port terminal session for
embedded/hardware communication.
"""

from __future__ import annotations

import threading
import queue
import time
import logging

log = logging.getLogger(__name__)


class SerialSession:
    """Manages a serial port connection with threaded I/O."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        bytesize: int = 8,
        parity: str = "N",
        stopbits: float = 1,
        timeout: float | None = 0.1,
    ):
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout

        self._serial = None
        self.alive = False
        self.is_ready = False
        self.input_queue: queue.Queue[str | None] = queue.Queue()

    def connect(self) -> bool:
        """Open the serial port. Returns True on success."""
        try:
            import serial

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
            self.alive = True
            self.is_ready = True
            log.info("Serial connected to %s @ %d baud", self.port, self.baudrate)
            return True
        except Exception as exc:
            log.error("Serial connection failed: %s", exc)
            self.alive = False
            self.is_ready = False
            return False

    def read(self, size: int = 4096) -> str | None:
        """Non-blocking read from the serial port."""
        if not self._serial or not self._serial.is_open:
            return None
        try:
            if self._serial.in_waiting:
                data = self._serial.read(min(size, self._serial.in_waiting))
                return data.decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    def write(self, data: str) -> None:
        """Send data to the serial port."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(data.encode("utf-8", errors="replace"))
            except Exception:
                pass

    def close(self) -> None:
        """Close the serial port."""
        self.alive = False
        self.is_ready = False
        self.input_queue.put(None)
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    @property
    def is_connected(self) -> bool:
        return self.alive and self._serial is not None and self._serial.is_open

    @staticmethod
    def list_ports() -> list[str]:
        """List available serial ports on the system."""
        try:
            import serial.tools.list_ports
            return [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            return []

    def send_break(self, duration: float = 0.25) -> None:
        """Send a break signal."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.send_break(duration)
            except Exception:
                pass

    def set_dtr(self, state: bool) -> None:
        """Set the DTR (Data Terminal Ready) line."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.dtr = state
            except Exception:
                pass

    def set_rts(self, state: bool) -> None:
        """Set the RTS (Request To Send) line."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.rts = state
            except Exception:
                pass
