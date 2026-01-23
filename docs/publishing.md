# Publishing to PyPI / TestPyPI

This repo uses `setuptools` + `pyproject.toml`.

## 0) Pick a PyPI project name

PyPI project names must be unique. This repo uses `name = "openagentic-sdk"` (see `pyproject.toml`). If it's already taken, change `[project].name` before publishing.

## 1) Create credentials

- Create an account on TestPyPI and PyPI (enable 2FA).
- Create an API token (recommended) and use it with `twine`.

## 2) Install build tools

```bash
python -m pip install -U pip
python -m pip install -U build twine
```

## 3) Build distributions

```bash
python -m build
python -m twine check dist/*
```

## 4) Upload to TestPyPI first

```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI (note: many dependencies still come from PyPI via `--extra-index-url`):

```bash
python -m pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple openagentic-sdk
```

## 5) Upload to PyPI

```bash
python -m twine upload dist/*
```

## Windows notes (PowerShell)

If `pip` installs scripts to a user scripts directory, ensure it is on `PATH` (pip will print the exact path).
If `oa` isn't found after installation, try `python -m openagentic_cli chat` or add the printed scripts directory to `PATH`.

Optional (recommended): install ripgrep (`rg`) so the agent can search quickly when using shell tools:

```powershell
winget install BurntSushi.ripgrep.MSVC
```
