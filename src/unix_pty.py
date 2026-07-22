# -*- coding: utf-8 -*-
"""Unix PTY wrapper for Linux and macOS."""
import os
import sys
import threading
import select
import subprocess
import shlex

class UnixPTYEngine:
    def __init__(self, signals):
        self.signals = signals
        self.master_fd = None
        self.proc = None
        self.alive = False

    def start(self, cmd: str = "/bin/bash", cwd: str | None = None) -> bool:
        try:
            import pty
            master_fd, slave_fd = pty.openpty()
            self.master_fd = master_fd

            # Parse command
            args = shlex.split(cmd) if cmd else ["/bin/bash"]
            # Fallback for Windows-specific defaults when run on Unix
            if args == ["cmd.exe"] or args == ["powershell.exe"] or args == ["pwsh.exe"]:
                args = [os.environ.get("SHELL", "/bin/bash")]

            self.proc = subprocess.Popen(
                args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                preexec_fn=os.setsid,
                close_fds=True,
                cwd=cwd,
            )
            os.close(slave_fd)
            self.alive = True

            # Start reading thread
            threading.Thread(target=self._read_loop, daemon=True, name="unix-pty-reader").start()
            return True
        except Exception as e:
            sys.stderr.write(f"UnixPTYEngine failed: {e}\n")
            return False

    def write(self, data: str):
        if self.alive and self.master_fd is not None:
            try:
                os.write(self.master_fd, data.encode("utf-8"))
            except Exception:
                pass

    def kill(self):
        self.alive = False
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except Exception:
                pass
            self.master_fd = None

    def _read_loop(self):
        while self.alive and self.master_fd is not None:
            try:
                r, w, x = select.select([self.master_fd], [], [], 0.1)
                if self.master_fd in r:
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    self.signals.text_ready.emit(text)
            except Exception:
                break
        self.alive = False
        self.signals.exited.emit("[Process exited]")
