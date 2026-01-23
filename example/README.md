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

## Core

- `example/01_run_basic.py` — one-shot `run()`
- `example/02_query_streaming.py` — streaming `query()` events (`assistant.delta`)
- `example/03_query_messages_basic.py` — CAS-style `query_messages()` + partial streaming
- `example/04_client_conversation.py` — `OpenAgentSDKClient` multi-turn reuse
- `example/05_resume_session.py` — `resume=<session_id>` continues a session

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

## Subagents / MCP / Sessions

- `example/18_task_subagent.py` — `Task` tool spawns a subagent (`AgentDefinition`)
- `example/19_mcp_sdk_tool.py` — SDK-defined MCP tool via `@tool` + `create_sdk_mcp_server`
- `example/20_inspect_session_log.py` — print `meta.json` + tail `events.jsonl` for a session
