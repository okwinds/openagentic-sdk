# Open Agent SDK (Python) — 10 Hour Implementation Plan (v0.1)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Over ~10 hours, harden the current `packages/sdk/openagentic-sdk/` scaffold into a usable “v0.1” SDK: installable package, stable event model, approvals + hooks, OpenAI streaming, subagents, `.claude` loading, and documentation, while keeping the code pure-Python and offline-testable.

**Architecture:** Keep the layered split already started: runtime (loop) + providers + tools + permissions + hooks + sessions + project settings. Add the minimum missing “production shape” pieces: packaging, better defaults, streaming, richer `.claude` integration, and reliability rails (limits/redaction).

**Tech Stack:** Python 3.11+ (asyncio), stdlib (`urllib`, `subprocess`, `unittest`), optional `uv`/pip for editable install. No network in tests (use injected transports / fake providers).

---

## Baseline (0:00–0:15)

Confirm current green state:

- Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`
- Expected: PASS (all tests)

---

## Hour 1 (0:15–1:15): Make it installable + runnable without `PYTHONPATH`

### Task 1: Editable install + test runner docs

**Files:**
- Modify: `packages/sdk/openagentic-sdk/pyproject.toml`
- Modify: `packages/sdk/openagentic-sdk/README.md`
- Create: `packages/sdk/openagentic-sdk/tests/test_install_import.py`

**Step 1: Write the failing test**

`packages/sdk/openagentic-sdk/tests/test_install_import.py`

```py
import unittest

class TestInstallImport(unittest.TestCase):
    def test_import_when_installed(self) -> None:
        import openagentic_sdk  # noqa: F401
```

**Step 2: Run test to verify it fails**

Run (no PYTHONPATH, no install): `python3 -m unittest -q`
Workdir: `packages/sdk/openagentic-sdk`
Expected: FAIL with `ModuleNotFoundError: openagentic_sdk`

**Step 3: Update packaging config**

`packages/sdk/openagentic-sdk/pyproject.toml`:
- Add `project.scripts` (optional) for a smoke entrypoint later
- Ensure setuptools includes `openagentic_sdk` package

**Step 4: Verify editable install works**

Run: `python3 -m pip install -e packages/sdk/openagentic-sdk`
Expected: installs from local path, no downloads

Run: `python3 -m unittest discover -s packages/sdk/openagentic-sdk/tests -p 'test_*.py' -q`
Expected: PASS

**Step 5: Document it**

Update `packages/sdk/openagentic-sdk/README.md` to include:
- “editable install” path
- “tests without PYTHONPATH” path

---

## Hour 2 (1:15–2:15): Stabilize Event schema + JSONL format guarantees

### Task 2: Event compatibility rules + versioning

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/events.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/serialization.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_events_contract.py`

**Step 1: Write failing contract test**

Define a contract:
- every event must serialize to a JSON object with `type`
- unknown `type` must raise a clean error
- `HookEvent` must always serialize `hook_point` and `name`

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m unittest -q tests/test_events_contract.py`
Expected: FAIL until rules are enforced

**Step 3: Implement minimal contract checks**

Implement:
- `event_from_dict()` validates required keys for each known type
- add a top-level `sdk.event_version` constant (e.g. `"v0"`)

**Step 4: Run tests**

Expected: PASS

---

## Hour 3 (2:15–3:15): Sessions hardening (auditable, safer defaults)

### Task 3: Session root selection + redaction hooks

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/store.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/sessions/redaction.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_session_redaction.py`

**Step 1: Write failing test**

Test that the session store can optionally redact large stdout/stderr fields before writing events.

**Step 2: Implement minimal redaction**

Add a `redactor` callback to `FileSessionStore.append_event(...)` (optional).

**Step 3: Run tests**

Expected: PASS

---

## Hour 4 (3:15–4:15): Permissions UX (callback + interactive) + AskUserQuestion shape

### Task 4: Interactive approver module and structured approval context

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/gate.py`
- Create: `packages/sdk/openagentic-sdk/openagentic_sdk/permissions/interactive.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_permissions_prompt.py`

**Step 1: Write failing test**

Inject a fake “interactive input provider” (no real stdin) and verify:
- prompt mode denies when user answers “no”
- prompt mode allows when user answers “yes”

**Step 2: Implement**

Move `input()` logic out of `gate.py` into `interactive.py` and make it injectable for tests.

**Step 3: Run tests**

Expected: PASS

---

## Hour 5 (4:15–5:15): Tools polish (limits + better edit model)

### Task 5: Improve Edit safety + Bash output limits default

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/edit.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/tools/bash.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_edit_edge_cases.py`

**Step 1: Write failing tests**

- `Edit` should support `count=0` meaning “replace all” explicitly
- `Edit` should report actual replacements performed
- `Bash` should mark `stdout_truncated`/`stderr_truncated` booleans

**Step 2: Implement**

Make behavior explicit and predictable.

**Step 3: Run tests**

Expected: PASS

---

## Hour 6 (5:15–6:15): OpenAI streaming (SSE) support

### Task 6: Streaming parser with injected transport

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/providers/openai.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_openai_provider_streaming.py`

**Step 1: Write failing test**

Use a fake streaming transport that yields:
- text deltas
- tool-call deltas
- final done sentinel

Assert the provider yields incremental events or a streaming-friendly output representation.

**Step 2: Implement minimal streaming**

Option A (recommended): add `OpenAIProvider.stream(...) -> AsyncIterator[ProviderEvent]`
Keep `complete(...)` as non-streaming.

**Step 3: Run tests**

Expected: PASS

---

## Hour 7 (6:15–7:15): Runtime integrates streaming + tool schema mapping

### Task 7: Runtime supports provider streaming

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/api.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_streaming.py`

**Step 1: Write failing test**

Fake streaming provider yields deltas; runtime should emit `assistant.delta` events and then a final `assistant.message`/`result`.

**Step 2: Implement**

Keep compatibility with non-streaming providers.

**Step 3: Run tests**

Expected: PASS

---

## Hour 8 (7:15–8:15): `.claude` integration into prompts + skill index injection

### Task 8: Load `.claude` settings and expose to model

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/project/claude.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_runtime_claude_injection.py`

**Step 1: Write failing test**

Given a project fixture with:
- `CLAUDE.md`
- `.claude/skills/.../SKILL.md`

Assert runtime constructs an initial system “memory + skill index” message when `setting_sources=["project"]`.

**Step 2: Implement minimal injection**

Do not inline full skills; only include an index and instructions to use `Read` to open skill files.

**Step 3: Run tests**

Expected: PASS

---

## Hour 9 (8:15–9:15): Subagents (`Task`) polish + isolation rules

### Task 9: AgentDefinition tool scoping and output shaping

**Files:**
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/runtime.py`
- Modify: `packages/sdk/openagentic-sdk/openagentic_sdk/options.py`
- Create: `packages/sdk/openagentic-sdk/tests/test_task_tool_scoping.py`

**Step 1: Write failing test**

Child agent with restricted tools must not be able to call a disallowed tool; verify the child produces a `PermissionDenied` tool result and the parent still completes.

**Step 2: Implement**

Enforce `AgentDefinition.tools` as a strict allowlist override.

**Step 3: Run tests**

Expected: PASS

---

## Hour 10 (9:15–10:15): Docs, examples, and “v0.1” acceptance checklist

### Task 10: Examples and acceptance docs

**Files:**
- Modify: `packages/sdk/openagentic-sdk/README.md`
- Create: `packages/sdk/openagentic-sdk/examples/basic_query.py`
- Create: `packages/sdk/openagentic-sdk/examples/approvals.py`
- Create: `packages/sdk/openagentic-sdk/examples/subagents.py`

**Step 1: Write minimal examples**

- `basic_query.py`: show `query()` printing events
- `approvals.py`: callback approver that denies `Bash` but allows `Read/Grep`
- `subagents.py`: define a `worker` and call it via `Task`

**Step 2: Syntax check examples**

Run: `PYTHONPATH=packages/sdk/openagentic-sdk python3 -m py_compile packages/sdk/openagentic-sdk/examples/*.py`
Expected: success (no output)

**Step 3: Acceptance checklist**

Add a checklist to README:
- installable (`pip install -e`)
- tests pass
- tool loop works with fake provider
- sessions written
- hooks can rewrite/block
- `.claude` index loads
- Task works and streams child events

---

## Notes / Constraints

- No git commits are performed by default in this repo unless explicitly requested.
- Keep tests offline: all network behaviors must be transport-injected and mocked.
- MCP remains a placeholder: keep options fields and docs, but do not implement execution in this 10-hour window.

