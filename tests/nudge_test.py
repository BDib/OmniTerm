"""Test that cmd.exe handles line endings correctly via subprocess."""
import os
import time
import subprocess


def test_line_endings():
    """CRLF line endings should work for command execution."""
    log_file = "nudge.log"
    if os.path.exists(log_file):
        os.remove(log_file)

    shell = "cmd.exe" if os.name == "nt" else "/bin/sh"
    proc = subprocess.Popen(
        [shell],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        time.sleep(0.5)
        cmd_str = f"echo worked > {log_file}\r\n" if os.name == "nt" else f"echo worked > {log_file}\n"
        proc.stdin.write(cmd_str)
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
