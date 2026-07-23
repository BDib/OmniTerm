"""Test that typing 'exit' properly closes the ConPTY tab.

Verifies the v2.5.1 fix: kill() closes pipe handles to unblock ReadFile,
and GetExitCodeProcess safety net detects process termination.
"""
import os
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

@pytest.mark.skipif(os.name != "nt", reason="ConPTY is Windows-only")
class TestExitFix:
    """Test exit command closes the ConPTY tab."""

    def _pump_events(self, app, timeout_s=3.0):
        """Process Qt events for up to timeout_s seconds."""
        from PyQt6.QtCore import QElapsedTimer, QEventLoop
        timer = QElapsedTimer()
        timer.start()
        loop = QEventLoop()
        while timer.elapsed() < timeout_s * 1000:
            loop.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)

    def test_exit_closes_tab(self):
        """Typing 'exit' in a ConPTY shell should fire the exited signal within 3 seconds."""
        from PyQt6.QtWidgets import QApplication
        from conpty import ConPTYEngine

        app = QApplication.instance() or QApplication(sys.argv)

        engine = ConPTYEngine()
        exited_event = threading.Event()
        exit_msg = []

        def on_exit(msg):
            exit_msg.append(msg)
            exited_event.set()

        engine.exited.connect(on_exit)

        started = engine.start("cmd.exe")
        assert started, "ConPTY failed to start"
        assert engine.alive, "Engine should be alive after start"

        # Send 'exit' command
        engine.write("exit\r\n")

        # Pump events for up to 3 seconds, checking for the signal
        self._pump_events(app, timeout_s=3.0)

        assert exited_event.is_set(), (
            f"exited signal was not fired within 3s. "
            f"Engine alive={engine.alive}, session={engine._session}"
        )
        assert not engine.alive, "Engine should be dead after exit"
        assert exit_msg, "exit_msg should contain the exit message"

    def test_kill_unblocks_read_loop(self):
        """kill() should close pipe handles and unblock the read loop."""
        from PyQt6.QtWidgets import QApplication
        from conpty import ConPTYEngine

        app = QApplication.instance() or QApplication(sys.argv)

        engine = ConPTYEngine()
        exited_event = threading.Event()

        engine.exited.connect(lambda msg: exited_event.set())

        started = engine.start("cmd.exe")
        assert started, "ConPTY failed to start"

        # Kill immediately (shell is still running, ReadFile is blocking)
        engine.kill()

        # Pump events — kill() closes pipes, ReadFile unblocks, exited fires
        self._pump_events(app, timeout_s=2.0)

        assert exited_event.is_set(), (
            f"exited signal not fired after kill(). "
            f"Engine alive={engine.alive}, killed={engine._killed}"
        )
        assert not engine.alive

    def test_exit_closes_tab_integration(self):
        """Full integration: TerminalEngine + ConPTY -> exit -> signal chain works."""
        from PyQt6.QtWidgets import QApplication
        from terminal_core import TerminalEngine

        app = QApplication.instance() or QApplication(sys.argv)

        engine = TerminalEngine()
        exited_event = threading.Event()
        exit_msg = []

        def on_exit(msg):
            exit_msg.append(msg)
            exited_event.set()

        engine.signals.exited.connect(on_exit)

        started = engine.start("cmd.exe")
        assert started, "TerminalEngine failed to start"

        # Type 'exit'
        engine.write("exit\r\n")

        # Pump events for up to 3 seconds
        self._pump_events(app, timeout_s=3.0)

        assert exited_event.is_set(), (
            f"TerminalEngine.exited signal not fired within 3s. "
            f"alive={engine.alive}"
        )
        assert not engine.alive, "Engine should be dead after exit"
        assert exit_msg, "Should have exit message"
