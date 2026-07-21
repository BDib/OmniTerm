"""
Unit tests for CLI argument parsing and distribution features.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import VERSION


def test_version_string():
    """VERSION should be a valid semver-like string."""
    parts = VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
    print(f"  PASS: VERSION = {VERSION}")


def test_cli_args_help():
    """--help should not crash."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    assert "OmniTerm" in result.stdout
    assert "--shell" in result.stdout
    assert "--profile" in result.stdout
    assert "--plain" in result.stdout
    assert "--config" in result.stdout
    print("  PASS: --help output includes all flags")


def test_cli_args_version():
    """--version should print the version."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--version"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    assert VERSION in result.stdout
    print("  PASS: --version prints correct version")


def test_cli_shell_arg():
    """--shell argument should be accepted."""
    import subprocess
    # Just test that the arg is accepted (not that it runs)
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--shell", "cmd.exe", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    print("  PASS: --shell argument accepted")


def test_cli_profile_arg():
    """--profile argument should be accepted."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--profile", "powershell", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    print("  PASS: --profile argument accepted")


def test_cli_plain_arg():
    """--plain argument should be accepted."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--plain", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    print("  PASS: --plain argument accepted")


def test_cli_config_arg():
    """--config argument should be accepted."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "src/Main.py", "--config", "settings.toml", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0
    print("  PASS: --config argument accepted")


def test_settings_toml_embedded():
    """settings.toml should be present in the project root."""
    settings = Path(__file__).resolve().parent.parent / "settings.toml"
    assert settings.is_file()
    content = settings.read_text()
    assert "[profiles" in content
    assert "[keybindings]" in content
    print("  PASS: settings.toml is complete")


def test_spec_file_exists():
    """OmniTerm.spec should exist."""
    spec = Path(__file__).resolve().parent.parent / "OmniTerm.spec"
    assert spec.is_file()
    content = spec.read_text()
    assert "OmniTerm" in content
    assert "console=False" in content
    print("  PASS: OmniTerm.spec exists and is configured")


def test_build_script_exists():
    """build.bat should exist."""
    build = Path(__file__).resolve().parent.parent / "build.bat"
    assert build.is_file()
    print("  PASS: build.bat exists")


def test_ci_workflow_exists():
    """GitHub Actions CI workflow should exist."""
    ci = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"
    assert ci.is_file()
    content = ci.read_text()
    assert "python-version" in content
    assert "run_all" in content
    assert "pyinstaller" in content
    print("  PASS: CI workflow exists")


def run_all():
    print("Running distribution tests...")
    test_version_string()
    test_cli_args_help()
    test_cli_args_version()
    test_cli_shell_arg()
    test_cli_profile_arg()
    test_cli_plain_arg()
    test_cli_config_arg()
    test_settings_toml_embedded()
    test_spec_file_exists()
    test_build_script_exists()
    test_ci_workflow_exists()
    print("All distribution tests passed!\n")


if __name__ == "__main__":
    run_all()
