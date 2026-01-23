# PyPI Publishing Preparation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make this repo ready to build and publish to PyPI/TestPyPI with correct metadata, versioning, and clear instructions.

**Architecture:** Keep setuptools + `pyproject.toml` as the single source of packaging metadata. Ensure runtime reports the installed SDK version. Add a small publishing guide (`docs/publishing.md`) and a short README pointer.

**Tech Stack:** Python 3.11+, `setuptools`, `build`, `twine`.

---

### Task 1: Add/adjust PyPI metadata in `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

**Steps:**
- Set a non-placeholder version (e.g. `0.1.0`).
- Add basic metadata fields that PyPI expects (`authors`, `classifiers`, `urls`, etc.) without guessing a license.
- Keep `[project.scripts] oa = "openagentic_cli.__main__:main"`.
- Add `dev` extras to include `build` + `twine` for contributors.

---

### Task 2: Align version reporting at runtime

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/_version.py`
- Modify: `openagentic_cli/__init__.py`

**Steps:**
- Ensure `SystemInit.sdk_version` reports the installed package version (not a hard-coded string).
- Keep `openagentic_sdk.__version__` consistent with `pyproject.toml`.

---

### Task 3: Add publishing documentation

**Files:**
- Create: `docs/publishing.md`
- Modify: `README.md`

**Steps:**
- Document TestPyPI-first flow, then PyPI.
- Include Windows PowerShell notes (user installs, PATH, `winget`).
- Mention `rg` (ripgrep) as optional tooling for better agent ergonomics.

---

### Task 4: Verification

**Steps:**
- Run: `python3 -m unittest -q`
- (Optional, manual): `python -m pip install -U build twine` then `python -m build` and `python -m twine check dist/*`

