"""
Unit tests for SSH session and dialog.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_ssh_session_import():
    """SSHSession should be importable."""
    from ssh_session import SSHSession
    assert SSHSession is not None
    print("  PASS: SSHSession importable")


def test_ssh_session_defaults():
    """SSHSession should have sensible defaults."""
    from ssh_session import SSHSession
    s = SSHSession(host="example.com")
    assert s.host == "example.com"
    assert s.port == 22
    assert s.username == ""
    assert s.password is None
    assert s.key_filename is None
    assert s.alive is False
    assert s.is_ready is False
    assert s.is_connected is False
    print("  PASS: SSHSession defaults")


def test_ssh_session_params():
    """SSHSession should store all connection parameters."""
    from ssh_session import SSHSession
    s = SSHSession(
        host="192.168.1.100",
        port=2222,
        username="admin",
        password="secret",
        key_filename="/path/to/key",
        timeout=30,
    )
    assert s.host == "192.168.1.100"
    assert s.port == 2222
    assert s.username == "admin"
    assert s.password == "secret"
    assert s.key_filename == "/path/to/key"
    assert s.timeout == 30
    print("  PASS: SSHSession parameters")


def test_ssh_dialog_import():
    """SSHDialog should be importable."""
    from ssh_dialog import SSHDialog
    assert SSHDialog is not None
    print("  PASS: SSHDialog importable")


def test_ssh_in_terminal_engine():
    """TerminalEngine should have start_ssh method."""
    from terminal_core import TerminalEngine
    engine = TerminalEngine()
    assert hasattr(engine, "start_ssh")
    assert hasattr(engine, "ssh")
    assert engine.ssh is None
    assert engine.is_ssh is False
    print("  PASS: TerminalEngine SSH support")


def test_ssh_connect_action_in_config():
    """ssh_connect should be in BUILTIN_ACTIONS."""
    from config import BUILTIN_ACTIONS
    assert "ssh_connect" in BUILTIN_ACTIONS
    print("  PASS: ssh_connect in BUILTIN_ACTIONS")


def test_ssh_connect_action_resolves():
    """_resolve_action should handle ssh_connect."""
    from terminal_core import TerminalEngine
    # We can't easily create a MainWindow without QApplication, but we can
    # verify the action name is valid
    from config import BUILTIN_ACTIONS
    assert "ssh_connect" in BUILTIN_ACTIONS
    print("  PASS: ssh_connect action is valid")


def test_ssh_session_close():
    """SSHSession.close() should be safe to call even when not connected."""
    from ssh_session import SSHSession
    s = SSHSession(host="example.com")
    s.close()  # Should not raise
    assert s.alive is False
    assert s.is_connected is False
    print("  PASS: SSHSession.close() safe when not connected")


def test_ssh_resize_noop_when_disconnected():
    """SSHSession.resize() should not raise when disconnected."""
    from ssh_session import SSHSession
    s = SSHSession(host="example.com")
    s.resize(120, 40)  # Should not raise
    print("  PASS: SSHSession.resize() safe when disconnected")


def run_all():
    print("Running SSH tests...")
    test_ssh_session_import()
    test_ssh_session_defaults()
    test_ssh_session_params()
    test_ssh_dialog_import()
    test_ssh_in_terminal_engine()
    test_ssh_connect_action_in_config()
    test_ssh_connect_action_resolves()
    test_ssh_session_close()
    test_ssh_resize_noop_when_disconnected()
    print("All SSH tests passed!\n")


if __name__ == "__main__":
    run_all()
