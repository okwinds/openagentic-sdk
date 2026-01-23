# Examples Output Verbosity Toggle — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `example/*.py` output human-friendly by default, with a `--debug` (or env var) toggle to show verbose event/tool debug output when needed.

**Architecture:** Add a shared `EventPrinter` helper in `example/_common.py` that consumes runtime events and prints either minimal (assistant text only) or verbose (tool/hook/session details). Update each example to route its event loop output through the helper.

**Tech Stack:** Python 3.11+, stdlib only.

---

### Task 1: Add example debug flag + EventPrinter

**Files:**
- Modify: `example/_common.py`

**Step 1:** Add `example_debug_enabled()` that reads:
- `--debug` in argv OR
- `OPEN_AGENT_SDK_EXAMPLE_DEBUG=1`

**Step 2:** Add `EventPrinter` with:
- default: print assistant text (deltas + final message), optionally prefix agent name
- debug: additionally print concise tool/hook/result summaries

**Step 3:** Keep output stable and non-“dataclass dump” in default mode.

---

### Task 2: Refactor examples to use EventPrinter

**Files:**
- Modify: `example/06_tool_read.py`
- Modify: `example/07_tool_write.py`
- Modify: `example/08_tool_edit.py`
- Modify: `example/09_tool_bash.py`
- Modify: `example/10_tool_glob_grep.py`
- Modify: `example/11_permissions_prompt_interactive.py`
- Modify: `example/12_permissions_prompt_noninteractive.py`
- Modify: `example/13_permissions_callback.py`
- Modify: `example/14_hooks_rewrite_tool_input.py`
- Modify: `example/15_hooks_block_tool.py`
- Modify: `example/16_slash_command.py`
- Modify: `example/17_skill_list_load_activate.py`
- Modify: `example/18_task_subagent.py`
- Modify: `example/19_mcp_sdk_tool.py`

**Step 1:** Replace per-event “print(ev)” with `EventPrinter.on_event(ev)`.

**Step 2:** Ensure non-interactive permission example still prints its headings and shows the user question succinctly.

---

### Task 3: Update docs + verification

**Files:**
- Modify: `example/README.md`

**Step 1:** Document:
- `--debug`
- `OPEN_AGENT_SDK_EXAMPLE_DEBUG=1`

**Step 2:** Run:
- `python3 -m unittest -q`

