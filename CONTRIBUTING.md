# Contributing to OmniTerm

## Getting Started

```bash
git clone https://github.com/BDib/OmniTerm.git
cd OmniTerm
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pytest ruff
python src/Main.py
```

## Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes in `src/`
3. Add/update tests in `tests/`
4. Run tests: `python -m pytest tests/ -v`
5. Lint: `ruff check src/ tests/ --select E402,F`
6. Commit with a descriptive message
7. Push and create a Pull Request

## Code Style

- Linting: `ruff check src/ tests/ --select E402,F`
- No line length limit (E501 disabled)
- Type hints where practical
- Brief docstrings for public APIs

## Testing

All tests must pass before submitting a PR. Tests run on Python 3.11–3.13 via GitHub Actions.

## Reporting Issues

Use [GitHub Issues](https://github.com/BDib/OmniTerm/issues). Include:
- Windows version, Python version
- Steps to reproduce
- Expected vs actual behavior
