"""
Unit tests for serial console and WSL integration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_serial_session_import():
    """SerialSession should be importable."""
    from serial_session import SerialSession
    assert SerialSession is not None
    print("  PASS: SerialSession importable")


def test_serial_session_defaults():
    """SerialSession should have sensible defaults."""
    from serial_session import SerialSession
    s = SerialSession(port="COM3")
    assert s.port == "COM3"
    assert s.baudrate == 115200
    assert s.bytesize == 8
    assert s.parity == "N"
    assert s.stopbits == 1
    assert s.alive is False
    assert s.is_connected is False
    print("  PASS: SerialSession defaults")


def test_serial_session_params():
    """SerialSession should store all connection parameters."""
    from serial_session import SerialSession
    s = SerialSession(
        port="/dev/ttyUSB0",
        baudrate=9600,
        bytesize=7,
        parity="E",
        stopbits=2,
    )
    assert s.port == "/dev/ttyUSB0"
    assert s.baudrate == 9600
    assert s.bytesize == 7
    assert s.parity == "E"
    assert s.stopbits == 2
    print("  PASS: SerialSession parameters")


def test_serial_session_close():
    """SerialSession.close() should be safe when not connected."""
    from serial_session import SerialSession
    s = SerialSession(port="COM99")
    s.close()
    assert s.alive is False
    assert s.is_connected is False
    print("  PASS: SerialSession.close() safe")


def test_serial_session_list_ports():
    """SerialSession.list_ports() should return a list."""
    from serial_session import SerialSession
    ports = SerialSession.list_ports()
    assert isinstance(ports, list)
    print(f"  PASS: SerialSession.list_ports() returns {len(ports)} ports")


def test_serial_dialog_import():
    """SerialDialog should be importable."""
    from serial_dialog import SerialDialog
    assert SerialDialog is not None
    print("  PASS: SerialDialog importable")


def test_serial_baud_rates():
    """SerialDialog should have standard baud rates."""
    from serial_dialog import SerialDialog
    assert 115200 in SerialDialog.BAUD_RATES
    assert 9600 in SerialDialog.BAUD_RATES
    assert 921600 in SerialDialog.BAUD_RATES
    print("  PASS: SerialDialog baud rates")


def test_wsl_manager_import():
    """WSLManager should be importable."""
    from wsl_manager import WSLManager
    assert WSLManager is not None
    print("  PASS: WSLManager importable")


def test_wsl_manager_is_available():
    """WSLManager.is_available() should return a bool."""
    from wsl_manager import WSLManager
    result = WSLManager.is_available()
    assert isinstance(result, bool)
    print(f"  PASS: WSL available = {result}")


def test_wsl_list_distributions():
    """WSLManager.list_distributions() should return a list."""
    from wsl_manager import WSLManager
    distros = WSLManager.list_distributions()
    assert isinstance(distros, list)
    for d in distros:
        assert "name" in d
        assert "status" in d
        assert "version" in d
    print(f"  PASS: WSL distributions = {[d['name'] for d in distros]}")


def test_wsl_get_shell_command():
    """WSLManager.get_shell_command() should return valid commands."""
    from wsl_manager import WSLManager
    assert WSLManager.get_shell_command() == "wsl"
    assert WSLManager.get_shell_command("Ubuntu") == "wsl --distribution Ubuntu"
    assert WSLManager.get_shell_command("Debian") == "wsl --distribution Debian"
    print("  PASS: WSL shell commands")


def test_wsl_get_default_distribution():
    """WSLManager.get_default_distribution() should return str or None."""
    from wsl_manager import WSLManager
    result = WSLManager.get_default_distribution()
    assert result is None or isinstance(result, str)
    print(f"  PASS: WSL default distribution = {result}")


def test_wsl_list_shells():
    """WSLManager.list_shells() should return a list."""
    from wsl_manager import WSLManager
    shells = WSLManager.list_shells()
    assert isinstance(shells, list)
    print(f"  PASS: WSL shells = {shells[:3]}...")


def test_serial_in_terminal_engine():
    """TerminalEngine should have start_serial method."""
    from terminal_core import TerminalEngine
    engine = TerminalEngine()
    assert hasattr(engine, "start_serial")
    assert hasattr(engine, "serial")
    assert engine.serial is None
    assert engine.is_serial is False
    print("  PASS: TerminalEngine serial support")


def test_wsl_connect_action():
    """wsl_connect should be in BUILTIN_ACTIONS."""
    from config import BUILTIN_ACTIONS
    assert "wsl_connect" in BUILTIN_ACTIONS
    assert "serial_connect" in BUILTIN_ACTIONS
    print("  PASS: wsl_connect and serial_connect in BUILTIN_ACTIONS")


def run_all():
    print("Running serial/WSL tests...")
    test_serial_session_import()
    test_serial_session_defaults()
    test_serial_session_params()
    test_serial_session_close()
    test_serial_session_list_ports()
    test_serial_dialog_import()
    test_serial_baud_rates()
    test_wsl_manager_import()
    test_wsl_manager_is_available()
    test_wsl_list_distributions()
    test_wsl_get_shell_command()
    test_wsl_get_default_distribution()
    test_wsl_list_shells()
    test_serial_in_terminal_engine()
    test_wsl_connect_action()
    print("All serial/WSL tests passed!\n")


if __name__ == "__main__":
    run_all()
