# Open Agent SDK (Python) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a pure-Python “Open Agent SDK” with CAS-like `query()` streaming + `run()` one-shot, built-in tools (Read/Write/Edit/Glob/Grep/Bash/WebFetch/WebSearch), approvals, hooks, sessions (filesystem), `.claude` project settings, and subagents (`Task`), with OpenAI provider implemented first.

**Architecture:** Split the SDK into runtime (agent loop), provider adapters (OpenAI first), tool registry + implementations, permissions (callback + interactive), hooks (audit/block/rewrite), `.claude` settings loader, and filesystem session store that writes `events.jsonl`.

**Tech Stack:** Python 3.11+, asyncio, `pydantic` (schemas + JSON), `httpx` (HTTP + streaming), `platformdirs` (session storage paths), `pytest` + `pytest-asyncio` (tests), `pytest-httpx` (HTTP mocking).

---

## Conventions

- New package root: `packages/sdk/open-agent-sdk/`
- Python module name: `open_agent_sdk`
- Default session store dir: use `platformdirs.user_data_dir("open-agent-sdk")` (exact path differs by OS)
- Tests are offline by default; all HTTP calls must be mocked.

---

### Task 1: Scaffold the Python package

**Files:**
- Create: `packages/sdk/open-agent-sdk/pyproject.toml`
- Create: `packages/sdk/open-agent-sdk/README.md`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/__init__.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/_version.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_imports.py`

**Step 1: Write the failing test**

`packages/sdk/open-agent-sdk/tests/test_imports.py`

```py
def test_import_open_agent_sdk():
    import open_agent_sdk  # noqa: F401
```

**Step 2: Run test to verify it fails**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'open_agent_sdk'`

**Step 3: Write minimal implementation**

`packages/sdk/open-agent-sdk/open_agent_sdk/__init__.py`

```py
from ._version import __version__

__all__ = ["__version__"]
```

`packages/sdk/open-agent-sdk/open_agent_sdk/_version.py`

```py
__version__ = "0.0.0"
```

**Step 4: Add packaging metadata**

`packages/sdk/open-agent-sdk/pyproject.toml` (minimal)

```toml
[project]
name = "open-agent-sdk"
version = "0.0.0"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.6",
  "httpx>=0.27",
  "platformdirs>=4.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "pytest-httpx>=0.30",
]

[build-system]
requires = ["hatchling>=1.24"]
build-backend = "hatchling.build"
```

**Step 5: Run test to verify it passes**

Run: `uv sync --dev --project packages/sdk/open-agent-sdk`

Expected: installs deps successfully

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q`

Expected: PASS (`1 passed`)

---

### Task 2: Define the event model + JSONL roundtrip

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/events.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/serialization.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_events_roundtrip.py`

**Step 1: Write the failing test**

`packages/sdk/open-agent-sdk/tests/test_events_roundtrip.py`

```py
from open_agent_sdk.events import SystemInit
from open_agent_sdk.serialization import dumps_event, loads_event

def test_event_roundtrip():
    e1 = SystemInit(session_id="s1", cwd="/tmp", sdk_version="0.0.0")
    raw = dumps_event(e1)
    e2 = loads_event(raw)
    assert e2 == e1
```

**Step 2: Run test to verify it fails**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_events_roundtrip.py::test_event_roundtrip`

Expected: FAIL with import error or missing symbol

**Step 3: Write minimal implementation**

`packages/sdk/open-agent-sdk/open_agent_sdk/events.py`

```py
from __future__ import annotations

from typing import Literal, Optional, Union
from pydantic import BaseModel, Field

class EventBase(BaseModel):
    type: str

class SystemInit(EventBase):
    type: Literal["system.init"] = "system.init"
    session_id: str
    cwd: str
    sdk_version: str

Event = Union[SystemInit]
```

`packages/sdk/open-agent-sdk/open_agent_sdk/serialization.py`

```py
from __future__ import annotations

import json
from typing import Any
from .events import Event, SystemInit

_TYPE_MAP = {"system.init": SystemInit}

def dumps_event(event: Event) -> str:
    return event.model_dump_json()

def loads_event(raw: str) -> Event:
    obj: Any = json.loads(raw)
    cls = _TYPE_MAP[obj["type"]]
    return cls.model_validate(obj)
```

**Step 4: Run test to verify it passes**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_events_roundtrip.py::test_event_roundtrip`

Expected: PASS

---

### Task 3: Implement filesystem session store (events.jsonl)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/sessions/store.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/sessions/paths.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_session_store.py`

**Step 1: Write the failing test**

`packages/sdk/open-agent-sdk/tests/test_session_store.py`

```py
from open_agent_sdk.events import SystemInit
from open_agent_sdk.sessions.store import FileSessionStore

def test_session_store_writes_events(tmp_path):
    store = FileSessionStore(root_dir=tmp_path)
    sid = store.create_session()
    store.append_event(sid, SystemInit(session_id=sid, cwd="/x", sdk_version="0.0.0"))
    p = store.session_dir(sid) / "events.jsonl"
    assert p.exists()
    assert p.read_text().strip() != ""
```

**Step 2: Run test to verify it fails**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_session_store.py::test_session_store_writes_events`

Expected: FAIL (missing store)

**Step 3: Write minimal implementation**

- `create_session()` returns a new `session_id` (uuid)
- `append_event()` appends `dumps_event(event) + "\n"` to `events.jsonl`
- `session_dir()` returns `<root>/<session_id>/`

**Step 4: Run test to verify it passes**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_session_store.py::test_session_store_writes_events`

Expected: PASS

---

### Task 4: Tool interface + registry (Read/Glob/Grep first)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/base.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/registry.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/read.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/glob.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/grep.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_tools_read_glob_grep.py`

**Step 1: Write failing tests**

`packages/sdk/open-agent-sdk/tests/test_tools_read_glob_grep.py`

```py
from open_agent_sdk.tools.registry import ToolRegistry
from open_agent_sdk.tools.read import ReadTool

def test_read_tool_reads_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello")
    tools = ToolRegistry([ReadTool()])
    out = tools.get("Read").run_sync({"file_path": str(p)})
    assert out["content"] == "hello"
```

**Step 2: Run test to verify it fails**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_tools_read_glob_grep.py::test_read_tool_reads_file`

Expected: FAIL

**Step 3: Implement minimal tool base/registry and Read tool**

Define:

- Tool name is stable string (e.g. `"Read"`)
- Tool input/output are pydantic models or dicts
- Add helper `.run_sync()` for tests

**Step 4: Run test to verify it passes**

Expected: PASS

**Step 5: Add Glob and Grep tests + implementations**

Add test cases for:

- `Glob(pattern="**/*.txt", root=tmp_path)`
- `Grep(query="hello", file_glob="**/*.txt", root=tmp_path)`

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_tools_read_glob_grep.py`

Expected: PASS

---

### Task 5: Permissions gate + interactive approver

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/permissions/models.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/permissions/gate.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/permissions/interactive.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_permissions_gate.py`

**Step 1: Write failing tests**

```py
import asyncio
import pytest
from open_agent_sdk.permissions.gate import PermissionGate

@pytest.mark.asyncio
async def test_gate_denies_when_callback_returns_false():
    async def approver(req, ctx):
        return False
    gate = PermissionGate(permission_mode="callback", approver=approver, interactive=False)
    allowed = await gate.approve("Bash", {"command": "echo hi"}, context={})
    assert allowed is False
```

**Step 2: Run test to verify it fails**

Run: `uv run --project packages/sdk/open-agent-sdk pytest -q tests/test_permissions_gate.py::test_gate_denies_when_callback_returns_false`

Expected: FAIL

**Step 3: Implement `PermissionGate`**

Behavior:

- `permission_mode="callback"` uses `approver`
- `permission_mode="prompt"` uses interactive approver
- `permission_mode="bypass"` always allow
- `permission_mode="deny"` always deny

**Step 4: Run test to verify it passes**

Expected: PASS

---

### Task 6: Hooks (audit + block + rewrite tool I/O)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/hooks/models.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/hooks/engine.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_hooks_rewrite.py`

**Step 1: Write failing tests**

Test that a `PreToolUse` hook can rewrite `tool_input`, and a `PostToolUse` hook can truncate `tool_output`.

**Step 2: Run test to verify it fails**

**Step 3: Implement hooks**

Rules:

- Support tool-name matcher (simple glob or regex)
- Support actions: audit (no change), block, rewrite
- Enable message rewrite hooks behind `enable_message_rewrite_hooks` (default false)

**Step 4: Run tests to verify they pass**

---

### Task 7: Provider interface + OpenAI provider (non-streaming first)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/providers/base.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/providers/openai.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_openai_provider_non_stream.py`

**Step 1: Write failing tests (mock HTTP)**

Use `pytest_httpx` to mock OpenAI responses for a simple assistant message and a tool call.

**Step 2: Run test to verify it fails**

**Step 3: Implement minimal OpenAI call**

Implement a single request/response round:

- build request with messages + tool schema
- parse response into either:
  - assistant text, or
  - tool call (`ToolUse`)

**Step 4: Run test to verify it passes**

---

### Task 8: OpenAI streaming support (SSE)

**Files:**
- Modify: `packages/sdk/open-agent-sdk/open_agent_sdk/providers/openai.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_openai_provider_stream.py`

**Step 1: Write failing test**

Mock streaming response body with multiple `data: {json}\n\n` chunks and a terminal `[DONE]`.

**Step 2: Run test to verify it fails**

**Step 3: Implement streaming parser**

Yield:

- `AssistantDelta` events for text deltas
- `ToolUse` event when tool call is fully formed (or incremental assembly if needed)

**Step 4: Run test to verify it passes**

---

### Task 9: Runtime loop (`query()`), tool execution, and `run()`

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/options.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/runtime.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/api.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_runtime_tool_loop.py`

**Step 1: Write failing test using a fake provider**

Fake provider emits:

1) assistant tool call to `Read`
2) then assistant final message after `ToolResult`

Assert runtime yields `ToolUse`, executes tool, yields `ToolResult`, then `Result`.

**Step 2: Run test to verify it fails**

**Step 3: Implement minimal runtime**

Responsibilities:

- create session + emit `SystemInit`
- call provider
- permission-check tool use
- run tool
- apply hooks (pre/post tool use)
- persist events to session store
- stop on `Result` or `max_steps`

**Step 4: Implement `run()`**

- Collect events
- Return `RunResult(final_text, events, session_id, usage)`

**Step 5: Run tests to verify they pass**

---

### Task 10: `Task` tool (subagents)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/task.py`
- Modify: `packages/sdk/open-agent-sdk/open_agent_sdk/runtime.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_subagent_task.py`

**Step 1: Write failing test**

Trigger `Task` tool use and assert:

- child events carry `parent_tool_use_id`
- parent yields a `ToolResult` summarizing child output

**Step 2: Run test to verify it fails**

**Step 3: Implement subagent execution**

- spawn child runtime with its own session id
- stream child events through parent (optional in v1, but recommended)
- collect child final output for parent `ToolResult`

**Step 4: Run tests to verify they pass**

---

### Task 11: Implement remaining built-in tools (Write/Edit/Bash/WebFetch/WebSearch/Tavily)

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/write.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/edit.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/bash.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/web_fetch.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/web_search_tavily.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_tools_bash_web.py`

**Step 1: Write failing tests**

- `Write` creates file
- `Edit` replaces substring and validates old text exists
- `Bash` runs `echo hello` and captures stdout (with approvals bypassed in test)
- `WebFetch` mocked HTTP returns content
- `WebSearch` mocked Tavily response returns normalized results

**Step 2: Run tests to verify they fail**

**Step 3: Implement tools minimally**

Security rails:

- `WebFetch`: block localhost/private networks unless config allows
- `Bash`: default deny unless approved
- result truncation limits configurable

**Step 4: Run tests to verify they pass**

---

### Task 12: `.claude` settings loader + Skills/Commands integration

**Files:**
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/project/loader.py`
- Create: `packages/sdk/open-agent-sdk/open_agent_sdk/tools/slash_command.py`
- Create: `packages/sdk/open-agent-sdk/tests/test_project_claude_loader.py`

**Step 1: Write failing tests**

Create fixture directory with:

- `CLAUDE.md`
- `.claude/skills/example/SKILL.md`
- `.claude/commands/hello.md`

Assert loader returns:

- memory text (from CLAUDE.md)
- indexed skill list (name/path)
- command list

**Step 2: Run test to verify it fails**

**Step 3: Implement loader + SlashCommand tool**

`SlashCommand` reads `.claude/commands/<name>.md` and returns its text.

**Step 4: Run tests to verify they pass**

---

### Task 13: Docs + examples + MCP placeholder

**Files:**
- Modify: `packages/sdk/open-agent-sdk/README.md`
- Create: `packages/sdk/open-agent-sdk/examples/basic.py`
- Create: `packages/sdk/open-agent-sdk/examples/approvals.py`
- Create: `packages/sdk/open-agent-sdk/examples/subagents.py`

**Step 1: Add README sections**

- Install (`uv sync --dev --project ...`)
- Usage (`query`, `run`)
- Tools list
- Approvals/hook examples
- `.claude` settings support
- MCP placeholder section (API fields only, “not implemented yet”)

**Step 2: Add examples**

Examples should run without network if provider is swapped for a fake provider; otherwise document env vars for OpenAI/Tavily.

**Step 3: Smoke-test examples**

Run (syntax check): `uv run --project packages/sdk/open-agent-sdk python -m py_compile examples/*.py`

Expected: no output (success)

---

## Final verification

Run:

- `uv run --project packages/sdk/open-agent-sdk pytest -q`

Expected: PASS (all tests)

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-01-22-open-agent-sdk-python-implementation-plan.md`.

Two execution options:

1. **Subagent-Driven (this session)** — use `superpowers:subagent-driven-development`, dispatch one task at a time, review between tasks.
2. **Parallel Session (separate)** — open a new session in this worktree and use `superpowers:executing-plans` to run tasks with checkpoints.

Which approach do you want?

