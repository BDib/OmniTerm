# Contributing to OmniTerm

Thank you for your interest in contributing to OmniTerm! This guide will help you get started.

## Getting Started

### Prerequisites
- Python 3.10 or later
- Windows 10 build 17763+ (x64)
- Git

### Setup
```bash
git clone https://github.com/BDib/OmniTerm.git
cd OmniTerm
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/Main.py
```

### Development Dependencies
```bash
pip install pytest ruff pyinstaller nuitka
```

## Project Structure

```
src/              # All Python source code
tests/            # Test suites (12 suites, 141 tests)
installer/        # Inno Setup installer script
settings.toml     # Default configuration
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test suite
python -m pytest tests/test_keyboard.py -v
python -m pytest tests/test_rendering.py -v

# Run with quiet output
python -m pytest tests/ -q
```

All tests must pass before submitting a PR. Tests run on Python 3.10-3.13 via GitHub Actions.

## Code Style

- **Linting**: `ruff check src/ tests/ --select E402,F`
- **No line length limit** enforced (E501 disabled)
- **Type hints**: Used where practical
- **Docstrings**: Brief, for public APIs

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes in `src/`
3. Add/update tests in `tests/`
4. Run tests: `python -m pytest tests/ -v`
5. Commit with a descriptive message
6. Push and create a Pull Request

## Building

```bash
# Nuitka (default, fastest)
.\build.ps1

# PyInstaller (fallback)
.\build.ps1 pyinstaller

# Full release (build + installer)
.\build.ps1 installer

# Clean artifacts
.\build.ps1 clean
```

## Architecture Notes

- **ConPTY backend** (`conpty.py`) — Windows Pseudo Console API via ctypes, uses two separate pipes (input + output) to prevent echo loops
- **TerminalWidget** uses a QWidget with QTextEdit (output) + QTextEdit (input)
- Output is append-only — the shell handles all cursor movement and line editing
- ANSI parsing happens in `ansi_parser.py`, rendering in `ansi_renderer.py`
- The engine (`terminal_core.py`) manages ConPTY/SSH/Serial sessions with threaded I/O
- Configuration is in `settings.toml`, loaded by `config.py`
- 143 tests across 12 test suites, run with `python -m pytest tests/`

## Reporting Issues

Please use [GitHub Issues](https://github.com/BDib/OmniTerm/issues) to report bugs or request features. Include:
- Windows version
- Python version
- Steps to reproduce
- Expected vs actual behavior
