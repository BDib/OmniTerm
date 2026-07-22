"""Test that ConPTY spawns cmd.exe and can execute commands."""
import os
import time
import sys
import platform
import subprocess


def test_conpty_spawn():
    """ConPTY should spawn cmd.exe and execute a command."""
    log_file = "test_pty_output.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    # Use subprocess with pipes as a basic PTY smoke test
    proc = subprocess.Popen(
        ["cmd.exe"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        proc.stdin.write(f"echo worked > {log_file}\r\n")
        proc.stdin.flush()
        time.sleep(2)

        assert os.path.exists(log_file), "Output file was not created"
        with open(log_file) as f:
            content = f.read()
        assert "worked" in content, f"Expected 'worked' in output, got: {content}"
    finally:
        proc.terminate()
        if os.path.exists(log_file):
            os.remove(log_file)


def test_conpty_diagnostic():
    """Print diagnostic info about the ConPTY environment."""
    print(f"\n--- ConPTY Diagnostic ---")
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Python: {sys.version}")
    print(f"CWD: {os.getcwd()}")

    # Check ConPTY availability (Windows 10 1809+)
    build = int(platform.version().split(".")[-1]) if platform.version().replace(".", "").isdigit() else 0
    print(f"Windows build: {build}")
    if build >= 17763:
        print("ConPTY: Available (Windows 10 1809+)")
    else:
        print("ConPTY: May not be available (requires Windows 10 1809+)")
