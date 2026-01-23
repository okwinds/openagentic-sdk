# Open Agent SDK (Python) Examples Pack — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ~20 runnable `example/*.py` scripts that exercise the SDK end-to-end (runtime loop, tools, permissions, hooks, sessions, subagents, MCP SDK tools) so a human can manually smoke-test behavior.

**Architecture:** Create a tiny shared helper module (`example/_common.py`) for consistent sys.path setup, session root, and small provider stubs. Each example is deterministic/offline-first via scripted providers; a few examples optionally support real providers via env vars.

**Tech Stack:** Python 3.11+, stdlib only, existing `open_agent_sdk` modules.

---

### Task 1: Add shared example helper

**Files:**
- Create: `example/_common.py`

**Step 1:** Add sys.path bootstrap + repo-root detection.

**Step 2:** Add small scripted providers:
- `StepProvider` for deterministic `complete()` sequences.
- `StepStreamingProvider` for deterministic `stream()` sequences.

**Step 3:** Add helpers to:
- Build `OpenAgentOptions` with a default `.open-agent-sdk` session root under repo.
- Parse tool outputs from provider-native `tool` messages.

---

### Task 2: Core runtime + API examples (offline/deterministic)

**Files:**
- Create: `example/01_run_basic.py`
- Create: `example/02_query_streaming.py`
- Create: `example/03_query_messages_basic.py`
- Create: `example/04_client_conversation.py`
- Create: `example/05_resume_session.py`
- Create: `example/06_tool_read.py`
- Create: `example/07_tool_write.py`
- Create: `example/08_tool_edit.py`
- Create: `example/09_tool_bash.py`
- Create: `example/10_tool_glob_grep.py`

**Step 1:** Implement each script and ensure `python3 example/<script>.py` prints a clear “what happened” summary.

---

### Task 3: Permissions / hooks / project config examples

**Files:**
- Create: `example/11_permissions_prompt_interactive.py`
- Create: `example/12_permissions_prompt_noninteractive.py`
- Create: `example/13_permissions_callback.py`
- Create: `example/14_hooks_rewrite_tool_input.py`
- Create: `example/15_hooks_block_tool.py`
- Create: `example/16_slash_command.py`
- Create: `example/17_skill_list_load_activate.py`

**Step 1:** Keep examples deterministic by scripting tool calls.

**Step 2:** For the interactive permission example, prompt the user exactly once (approve/deny) and show the resulting event stream.

---

### Task 4: Subagents, MCP SDK tools, and session inspection examples

**Files:**
- Create: `example/18_task_subagent.py`
- Create: `example/19_mcp_sdk_tool.py`
- Create: `example/20_inspect_session_log.py`

**Step 1:** `Task` example demonstrates parent/child event streaming and returns a `ToolResult` with `child_session_id` + `final_text`.

**Step 2:** MCP example uses `open_agent_sdk.mcp.sdk.tool` + `create_sdk_mcp_server` and calls `mcp__<server>__<tool>`.

**Step 3:** Session inspection example prints `meta.json` + tail of `events.jsonl` for a chosen session id.

---

### Task 5: Example docs and smoke verification

**Files:**
- Create: `example/README.md`
- (Optional) Modify: `README.md` (add link to examples)

**Step 1:** Document how to run the examples and which env vars (if any) they use.

**Step 2:** Run unit tests and smoke-run a few examples:
- `python3 -m unittest -q`
- `python3 example/01_run_basic.py`
- `python3 example/06_tool_read.py`

