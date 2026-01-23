# OpenAgentic SDK Rename Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the *distribution/project branding* from `open-agent-sdk` → `openagentic-sdk`, and (optionally) rename defaults like the session directory, while keeping compatibility via shims/migration.

**Architecture:** Treat “PyPI distribution name” and “Python import package name” as separate layers. Keep CLI command `oa`. If doing a deep rename, keep `open_agent_sdk` / `open_agent_cli` as compatibility shims that forward to `openagentic_sdk` / `openagentic_cli`.

**Tech Stack:** Python 3.11+, `setuptools` + `pyproject.toml`, `unittest`.

---

## Scope Decision (do this first)

Pick one:

- **Option A: Distribution rename only**
  - PyPI name: `openagentic-sdk`
  - Imports remain: `open_agent_sdk`, `open_agent_cli`
  - CLI remains: `oa`
  - Session dir/env vars remain, minimizing breaking changes.

- **Option B: Deep rename (breaking-change managed)**
  - New imports: `openagentic_sdk` / `openagentic_cli`
  - Keep `open_agent_sdk` / `open_agent_cli` as shim packages (forward + `DeprecationWarning`)
  - Rename default session dir and env vars, with legacy alias/migration.

Everything below is written so Option A can be completed first, then Option B applied incrementally.

---

## Preflight (safe)

### Task 0: Worktree + baseline verification

**Files:** none

**Step 1: Create a worktree**

Run:
- `git status --porcelain`
- `git worktree add ../openagentic-sdk-rename -b rename/openagentic-sdk`

**Step 2: Baseline tests**

Run:
- `python3 -m unittest -q`
Expected: PASS

**Step 3: Capture rename inventory**

Run:
- `rg -n "openagentic-sdk|Open Agent SDK|\\.openagentic-sdk|OPENAGENTIC_SDK_HOME" -S .`
Expected: list of remaining rename targets.

---

## Option A (recommended): Distribution rename + branding sweep

### Task 1: Confirm packaging metadata uses `openagentic-sdk`

**Files:**
- Verify: `pyproject.toml`
- Verify: `docs/publishing.md`

**Step 1: Verify `pyproject.toml`**

Check:
- `[project].name = "openagentic-sdk"`
- `[project.scripts] oa = "openagentic_cli.__main__:main"`

**Step 2: Run unit tests**

Run: `python3 -m unittest -q`
Expected: PASS

---

### Task 2: Update user-facing docs to say “OpenAgentic SDK”

**Files:**
- Modify: `README.md`
- Modify: `README.zh_cn.md`
- Modify: `PROJECT_REPORT.md`

**Step 1: Rename headings + narrative text**

Targets:
- `Open Agent SDK` → `OpenAgentic SDK`
- `openagentic-sdk` (as a *project name* in prose) → `openagentic-sdk`

**Step 2: Keep import examples unchanged**

Do NOT change:
- `import openagentic_sdk` (only distribution name changes here)

**Step 3: Run unit tests**

Run: `python3 -m unittest -q`
Expected: PASS

---

### Task 3: Update CLI/SDK “prog/help” strings + tests

**Files:**
- Modify: `openagentic_sdk/__main__.py`
- Modify: `tests/test_main_help.py`
- Modify: `tests/__init__.py`

**Step 1: Change argparse `prog` branding**

Change:
- `argparse.ArgumentParser(prog="openagentic-sdk")`
To:
- `argparse.ArgumentParser(prog="openagentic-sdk")`

**Step 2: Update help assertion**

Change:
- `tests/test_main_help.py` expects `openagentic-sdk` in `--help` output.

**Step 3: Update test package docstring**

Change:
- `"""Test package for openagentic-sdk."""` → `"""Test package for openagentic-sdk."""`

**Step 4: Run targeted unit tests**

Run:
- `python3 -m unittest -q tests.test_main_help`
- `python3 -m unittest -q`
Expected: PASS

---

## Session directory + env var rename (optional, but matches “rename everything” intent)

### Task 4: Decide session directory strategy

Pick one:

- **Strategy 1 (compatible): keep `~/.openagentic-sdk`**
  - Only update branding text; zero migration risk.

- **Strategy 2 (rename with migration): default to `~/.openagentic-sdk`**
  - Support legacy `~/.openagentic-sdk` and migrate/auto-select when present.

---

### Task 5: Implement session root rename + migration (if Strategy 2)

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/client.py`
- Modify: `openagentic_cli/__main__.py`
- Modify: `openagentic_cli/repl.py`
- Modify: `openagentic_cli/args.py`
- Modify: `openagentic_sdk/tools/bash.py`
- Modify: `README.md`
- Modify: `README.zh_cn.md`
- Test: `tests/test_default_session_root_migration.py` (new)

**Step 1: Introduce a single helper for default session root**

Implement one function (in SDK, then reused by CLI) to:
- Prefer `OPENAGENTIC_SDK_HOME` if set.
- Else prefer `OPENAGENTIC_SDK_HOME` if set (legacy alias).
- Else use new default `~/.openagentic-sdk`.
- If new default does not exist but legacy `~/.openagentic-sdk` exists, use legacy path (or migrate; pick one consistent rule).

**Step 2: Update all callers to use the helper**

Replace hard-coded `.openagentic-sdk` strings in:
- runtime default root
- CLI default root
- repl fallback root
- bash tool output root
- `--session-root` help text

**Step 3: Add migration/selection tests**

Add `tests/test_default_session_root_migration.py` covering:
- `OPENAGENTIC_SDK_HOME` overrides everything
- legacy `OPENAGENTIC_SDK_HOME` still works
- legacy folder exists → chosen (or migrated) when new folder absent

**Step 4: Run unit tests**

Run:
- `python3 -m unittest -q tests.test_default_session_root_migration`
- `python3 -m unittest -q`
Expected: PASS

---

## Examples + internal docs sweep

### Task 6: Update examples to match session dir naming

**Files:**
- Modify: `example/_common.py`
- Modify: `example/README.md`
- Modify: `example/40_resume_continues_todos.py`
- Modify: `docs/plans/2026-01-23-openagentic-sdk-examples-plan.md`

**Step 1: Replace `.openagentic-sdk` with chosen session root**

If Strategy 1: keep `.openagentic-sdk` (no changes required).
If Strategy 2: rename to `.openagentic-sdk` (and optionally mention compatibility).

**Step 2: Run unit tests**

Run: `python3 -m unittest -q`
Expected: PASS

---

### Task 7: Decide how aggressive to be with historical `docs/plans/*`

Pick one:

- **Keep history**: do not rewrite old plans (recommended); add a short note in a new doc that “the project was previously named openagentic-sdk”.
- **Rewrite**: replace occurrences in all `docs/plans/*.md` (expect large diff; risk of breaking links/old context).

If rewriting:

**Files:**
- Modify: many under `docs/plans/`

**Steps:**
- Run: `rg -n "openagentic-sdk|\\.openagentic-sdk" docs/plans -S`
- Apply replacements in small batches.
- After each batch: `python3 -m unittest -q` (should be unaffected).

---

## Final Verification (required)

### Task 8: Full verification + build sanity

**Step 1: Unit tests**

Run: `python3 -m unittest -q`
Expected: PASS

**Step 2: Grep for leftovers (policy-based)**

Run:
- `rg -n "openagentic-sdk" -S .`
- `rg -n "\\.openagentic-sdk" -S .`
Expected: only the intentionally preserved legacy notes (if any).

**Step 3: Build distributions (optional but recommended)**

Run:
- `python -m pip install -U build twine`
- `python -m build`
- `python -m twine check dist/*`
Expected: PASS
