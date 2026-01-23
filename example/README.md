# Examples

All scripts here are runnable directly (they call a real OpenAI-compatible backend via `RIGHTCODE_*` env vars):

```bash
export RIGHTCODE_API_KEY="..."
export RIGHTCODE_BASE_URL="https://www.right.codes/codex/v1"   # optional
export RIGHTCODE_MODEL="gpt-5.2"                               # optional
export RIGHTCODE_TIMEOUT_S="120"                               # optional

python3 example/01_run_basic.py
```

Notes:
- `RIGHTCODE_API_KEY` is required (examples exit early if missing).
- Session logs are written under `.open-agent-sdk/` (gitignored).
- Some examples use `TemporaryDirectory()` for the working directory (so files are ephemeral).
- Examples that write files persist them under `.open-agent-sdk/example-artifacts/<example-id>/` and print the exact output path.
- If RIGHTCODE returns transient `HTTP 502/503/504`, examples retry by default (`RIGHTCODE_MAX_RETRIES=2`, `RIGHTCODE_RETRY_BACKOFF_S=0.5`).

## Output verbosity

- Default: prints only the assistant text (human-friendly).
- Debug: prints tool/hook/result summaries too.
  - CLI flag: `--debug`
  - Env var: `OPEN_AGENT_SDK_CONSOLE_DEBUG=1` (legacy: `OPEN_AGENT_SDK_EXAMPLE_DEBUG=1`)

## Core

- `example/01_run_basic.py` — one-shot `run()`
- `example/02_query_streaming.py` — streaming `query()` events (`assistant.delta`)
- `example/03_query_messages_basic.py` — CAS-style `query_messages()` + partial streaming
- `example/04_client_conversation.py` — `OpenAgentSDKClient` multi-turn reuse
- `example/05_resume_session.py` — `resume=<session_id>` continues a session
- `example/bugfix_auth.py` — real tool loop against `example/auth.py` (interactive approvals)

## Tools

- `example/06_tool_read.py` — `Read`
- `example/07_tool_write.py` — `Write`
- `example/08_tool_edit.py` — `Edit`
- `example/09_tool_bash.py` — `Bash`
- `example/10_tool_glob_grep.py` — `Glob` then `Grep`

## Permissions / Hooks / Project

- `example/11_permissions_prompt_interactive.py` — interactive approval prompt (`y/yes` to allow)
- `example/12_permissions_prompt_noninteractive.py` — non-interactive prompt mode with/without `user_answerer`
- `example/13_permissions_callback.py` — callback approver denies `Bash`
- `example/14_hooks_rewrite_tool_input.py` — pre-tool hook rewrites `Read` input
- `example/15_hooks_block_tool.py` — hook blocks `Bash` before execution
- `example/16_slash_command.py` — `SlashCommand` from `.claude/commands`
- `example/17_skill_list_load_activate.py` — `SkillList`/`SkillLoad`/`SkillActivate` + system prompt update
- `example/41_skill_main_process.py` — run `.claude/skills/main-process` (delegates to `drawing`)

## Subagents / MCP / Sessions

- `example/18_task_subagent.py` — `Task` tool spawns a subagent (`AgentDefinition`)
- `example/19_mcp_sdk_tool.py` — SDK-defined MCP tool via `@tool` + `create_sdk_mcp_server`
- `example/20_inspect_session_log.py` — print `meta.json` + tail `events.jsonl` for a session

## Advanced (more realistic workflows)

Web (requires network):
- `example/21_web_fetch_summarize.py` — `WebFetch` + in-tool summarization prompt
- `example/22_web_search_then_fetch_report.py` — `WebSearch` → `WebFetch` → `Write` report (`TAVILY_API_KEY` required); writes to `.open-agent-sdk/example-artifacts/22/report.md`
- `example/23_web_search_domain_filters.py` — `WebSearch` domain allowlist (`TAVILY_API_KEY` required)
- `example/33_web_fetch_json_extract.py` — `WebFetch` JSON endpoint + extraction prompt
- `example/34_web_fetch_compare_and_write.py` — fetch 2 pages and write comparison

Notebook:
- `example/24_notebook_edit_research_report.py` — generate a notebook report via `NotebookEdit`
- `example/25_notebook_edit_tutorial_builder.py` — replace + insert cells via `NotebookEdit`

Interaction + TODOs:
- `example/26_ask_user_question_onboarding.py` — `AskUserQuestion` → `TodoWrite` (interactive answers)
- `example/27_todo_write_create_list.py` — create a TODO list via `TodoWrite`
- `example/28_todo_write_iterate_status.py` — update TODO statuses via repeated `TodoWrite`
- `example/29_research_to_todos.py` — `WebSearch` → `TodoWrite` (`TAVILY_API_KEY` required)
- `example/30_project_onboarding_notes.py` — `Read`/`Grep`/`Write` + `TodoWrite`
- `example/40_resume_continues_todos.py` — `resume` + persisted `todos.json`

Bash-based (requires `bash` in PATH):
- `example/31_generate_changelog_from_git.py` — `Bash` git log → `Write` changelog
- `example/32_triage_build_error_and_fix.py` — `Bash` compile error → `Edit` fix → `Bash` re-check
- `example/35_file_refactor_with_checks.py` — `Read`/`Edit` + `Bash` checks

Hooks / restrictions / MCP pipelines:
- `example/36_hooks_redact_sensitive_read.py` — post-tool hook redacts `Read` output
- `example/37_allowed_tools_sandbox_demo.py` — `allowed_tools` denial + recovery
- `example/38_mcp_two_tools_pipeline.py` — compose two MCP SDK tools
- `example/39_multi_turn_client_workflow.py` — multi-turn `OpenAgentSDKClient` + `TodoWrite`
