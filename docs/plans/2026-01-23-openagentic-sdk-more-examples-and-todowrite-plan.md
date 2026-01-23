# More Real-Backend Examples + TodoWrite Tool — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 20 additional, more realistic `example/*.py` scripts (real RIGHTCODE backend) and implement the missing `TodoWrite` tool (CAS-compatible I/O) so the examples can cover daily “agent SDK” usage patterns end-to-end.

**Architecture:** Implement `TodoWrite` as a real tool registered in `default_tool_registry()` with OpenAI tool schema, and handle session persistence in `AgentRuntime._run_tool_call()` by writing `todos.json` under the session dir. Add examples `21_*.py` … `40_*.py` that combine tools (web → summarize → write, notebook generation, TODO workflows, interactive Q&A, restricted tools, etc.) while keeping outputs human-friendly via `EventPrinter`.

**Tech Stack:** Python 3.11+, stdlib only, existing `openagentic_sdk` runtime/tools/sessions/hooks/permissions/providers.

---

### Task 1: Implement `TodoWrite` tool

**Files:**
- Create: `openagentic_sdk/tools/todo_write.py`
- Modify: `openagentic_sdk/tools/defaults.py`
- Modify: `openagentic_sdk/tools/openai.py`
- Modify: `openagentic_sdk/runtime.py`

**Step 1: Write failing test for registry + runtime**
- Add tests proving:
  - `default_tool_registry().names()` includes `TodoWrite`
  - A tool call to `TodoWrite` returns CAS-shaped output (`message`, `stats`)
  - Runtime persists a `todos.json` file under the session directory

**Step 2: Implement `TodoWriteTool`**
- Validate input shape:
  - `todos` is a non-empty list of objects
  - Each todo has `content` (str), `activeForm` (str), `status` in {pending,in_progress,completed}
- Compute stats and return:
  - `{"message": "...", "stats": {...}}`

**Step 3: Add OpenAI schema mapping**
- Add `TodoWrite` to `tool_schemas_for_openai()` with the CAS schema.

**Step 4: Persist todos in runtime**
- In `AgentRuntime._run_tool_call()`, add a `TodoWrite` special-case:
  - Run the tool to get output (and reuse validation/stats)
  - Write `todos.json` to `store.session_dir(session_id)/todos.json` with the todos list
  - Append `ToolResult`

---

### Task 2: Add examples 21–40 (real RIGHTCODE backend)

**Files:**
- Create: `example/21_web_fetch_summarize.py`
- Create: `example/22_web_search_then_fetch_report.py` (requires `TAVILY_API_KEY`)
- Create: `example/23_web_search_domain_filters.py` (requires `TAVILY_API_KEY`)
- Create: `example/24_notebook_edit_research_report.py`
- Create: `example/25_notebook_edit_tutorial_builder.py`
- Create: `example/26_ask_user_question_onboarding.py` (interactive via `user_answerer`)
- Create: `example/27_todo_write_create_list.py`
- Create: `example/28_todo_write_iterate_status.py`
- Create: `example/29_research_to_todos.py` (requires `TAVILY_API_KEY`)
- Create: `example/30_project_onboarding_notes.py` (Read/Grep/Write/TodoWrite)
- Create: `example/31_generate_changelog_from_git.py` (Bash/Write; repo cwd)
- Create: `example/32_triage_test_failures.py` (Bash/Grep/Write)
- Create: `example/33_web_fetch_json_extract.py`
- Create: `example/34_web_fetch_compare_and_update.py`
- Create: `example/35_file_refactor_with_checks.py` (Read/Edit/Bash)
- Create: `example/36_hooks_redact_sensitive_read.py`
- Create: `example/37_allowed_tools_sandbox_demo.py`
- Create: `example/38_mcp_two_tools_pipeline.py`
- Create: `example/39_multi_turn_client_workflow.py`
- Create: `example/40_resume_continues_todos.py`

**Guidelines:**
- Use `rightcode_options()` from `example/_common.py`.
- Use `EventPrinter` for output (default minimal, `--debug` optional).
- For examples that require extra keys, preflight-check env vars and exit with a clear message.
- Keep each script runnable independently.

---

### Task 3: Update examples docs and verify

**Files:**
- Modify: `example/README.md`

**Step 1:** Add an index entry for examples 21–40 and note which need `TAVILY_API_KEY`.

**Step 2:** Run unit tests:
- `python3 -m unittest -q`

