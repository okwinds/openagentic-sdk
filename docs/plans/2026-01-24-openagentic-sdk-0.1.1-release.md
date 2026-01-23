# OpenAgentic SDK 0.1.1 Release Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update README docs for `uv` install/CLI usage + bump version to `0.1.1` + publish to PyPI.

**Architecture:** No runtime changes. Only documentation updates, a version bump in packaging metadata, and a verified build+upload via `twine`.

**Tech Stack:** Python 3.11+, setuptools (`pyproject.toml`), `build`, `twine`.

### Task 1: Update English README for uv + CLI

**Files:**
- Modify: `README.md`

**Step 1: Add uv-based install instructions**
- Add a short section showing `uv init`, `uv add openagentic-sdk`, and running the CLI via `uv run oa chat` / `uv run oa run "..."`.

**Step 2: Clarify required environment variables**
- Document CLI defaults (RIGHTCODE backend) and required `RIGHTCODE_API_KEY` plus optional `RIGHTCODE_BASE_URL`, `RIGHTCODE_MODEL`, `RIGHTCODE_TIMEOUT_S`.

**Step 3: Add Windows PowerShell examples**
- Show `$env:RIGHTCODE_API_KEY="..."` and `uv run oa --help`.

**Step 4: Verify docs are consistent**
- Ensure references to the CLI entrypoint `oa` remain correct and examples don’t assume `pip` only.

### Task 2: Update Chinese README for uv + CLI

**Files:**
- Modify: `README.zh_cn.md`

**Step 1: Add uv-based install instructions**
- Mirror the English section for uv workflows in PowerShell.

**Step 2: Clarify required environment variables**
- Mirror the English env var list and explain defaults.

### Task 3: Bump version to 0.1.1

**Files:**
- Modify: `pyproject.toml`
- Modify: `openagentic_sdk/_version.py`

**Step 1: Update versions**
- Change `0.1.0` → `0.1.1` in both places.

**Step 2: Sanity check**
Run: `python3 -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"`
Expected: `0.1.1`

### Task 4: Verify tests and build

**Files:**
- (no code changes expected)

**Step 1: Run unit tests**
Run: `python3 -m unittest -q`
Expected: `OK`

**Step 2: Build artifacts**
Run: `.venv/bin/python -m build --no-isolation`
Expected: Creates `dist/openagentic_sdk-0.1.1-...whl` and `dist/openagentic_sdk-0.1.1.tar.gz`

**Step 3: Twine check**
Run: `.venv/bin/twine check dist/*`
Expected: `PASSED` for both artifacts

### Task 5: Upload to PyPI

**Files:**
- Uses: `.pypirc` (do not commit)

**Step 1: Upload**
Run: `.venv/bin/twine upload --config-file .pypirc -r pypi dist/*`
Expected: Upload succeeds and prints a `pypi.org/project/openagentic-sdk/0.1.1/` URL.

