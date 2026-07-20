"""
Windows Subsystem for Linux (WSL) integration for OmniTerm.

Auto-detects installed WSL distributions and provides shell commands
for each one.
"""

from __future__ import annotations

import subprocess
import logging

log = logging.getLogger(__name__)


class WSLError(Exception):
    """Raised when WSL operations fail."""
    pass


class WSLManager:
    """Manages WSL distribution discovery and launching."""

    @staticmethod
    def is_available() -> bool:
        """Check if WSL is installed and available."""
        try:
            result = subprocess.run(
                ["wsl", "--status"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False

    @staticmethod
    def list_distributions() -> list[dict[str, str]]:
        """List installed WSL distributions.

        Returns a list of dicts with keys: name, status, version.
        """
        try:
            result = subprocess.run(
                ["wsl", "--list", "--verbose"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            if result.returncode != 0:
                return []

            # wsl --list outputs UTF-16LE on Windows
            try:
                text = result.stdout.decode("utf-16-le")
            except Exception:
                text = result.stdout.decode("utf-8", errors="replace")

            distributions = []
            for line in text.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("NAME") or line.startswith("------"):
                    continue
                line = line.lstrip("*").strip()
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    status = parts[1] if len(parts) > 1 else "Running"
                    version = parts[2] if len(parts) > 2 else "2"
                    distributions.append({
                        "name": name,
                        "status": status,
                        "version": version,
                    })
            return distributions

        except Exception as exc:
            log.warning("Failed to list WSL distributions: %s", exc)
            return []

    @staticmethod
    def get_default_distribution() -> str | None:
        """Get the default WSL distribution name."""
        distros = WSLManager.list_distributions()
        if distros:
            return distros[0]["name"]
        return None

    @staticmethod
    def get_shell_command(distribution: str | None = None) -> str:
        """Get the shell command for a WSL distribution.

        If *distribution* is None, uses the default distribution.
        """
        if distribution:
            return f"wsl --distribution {distribution}"
        return "wsl"

    @staticmethod
    def list_shells(distribution: str | None = None) -> list[str]:
        """List available shells in a WSL distribution."""
        try:
            cmd = WSLManager.get_shell_command(distribution)
            result = subprocess.run(
                [cmd, "--", "cat", "/etc/shells"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            shells = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    shells.append(line)
            return shells
        except Exception:
            return ["/bin/bash", "/bin/sh"]

    @staticmethod
    def get_distribution_info(name: str) -> dict[str, str] | None:
        """Get detailed info about a specific distribution."""
        distros = WSLManager.list_distributions()
        for d in distros:
            if d["name"] == name:
                return d
        return None
