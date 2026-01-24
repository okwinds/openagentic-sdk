# OpenAgentic SDK (Python) Skills & Tools Guide

This document describes how this repository implements tools, skills, and the
agent runtime loop.

Scope:
- Codebase: `openagentic_sdk/` + `openagentic_cli/`
- Protocols: OpenAI Responses API style (preferred) and legacy chat-messages style

## Tools (Python)

### Core types

- Tool interface: `openagentic_sdk/tools/base.py`
  - `Tool.run(tool_input, ctx) -> Any` (async)
  - `Tool.run_sync(...)` convenience wrapper
- Context passed to tools: `openagentic_sdk/tools/base.py`
  - `ToolContext(cwd, project_dir)`

### Registry

- `ToolRegistry`: `openagentic_sdk/tools/registry.py`
  - `register(tool)`
  - `get(name)`
  - `names()`
- Default built-in registry: `openagentic_sdk/tools/defaults.py`
  - Built-ins include `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `WebFetch`, `WebSearch`, etc.

### Tool schemas sent to the model

The runtime builds tool schemas every step.

- Legacy chat-completions style schema:
  - `openagentic_sdk/tools/openai.py` (`tool_schemas_for_openai`)
- Responses API style tool schema:
  - `openagentic_sdk/tools/openai_responses.py` (`tool_schemas_for_responses`)

Tool descriptions are loaded from template files:
- `openagentic_sdk/tool_prompts/*.txt`
- Loader: `openagentic_sdk/tool_prompts/loader.py`

## Permissions

Permission checks happen before tool execution.

- Gate implementation: `openagentic_sdk/permissions/gate.py`
  - Modes: `default`, `prompt`, `callback`, `bypass`, `deny`, `acceptEdits`
  - In `default` mode, a small allowlist of safe tools is auto-approved.

The CLI can run interactively and prompt the user:
- REPL: `openagentic_cli/repl.py`
- CLI permission policy: `openagentic_cli/permissions.py`

## Skills and .claude Compatibility

This repo supports a Claude-style on-disk project layout.

### Where skills are discovered

- Indexer: `openagentic_sdk/skills/index.py`
- Search roots (in precedence order):
  1) Global skill roots under the SDK home (default: `~/.openagentic-sdk`)
  2) Project-local `.claude/` under `project_dir`

Within each root, both directories are supported:
- `skill/**/SKILL.md`
- `skills/**/SKILL.md`

### Skill tool

- Tool implementation: `openagentic_sdk/tools/skill.py`
  - Loads a skill by name
  - Returns the full skill Markdown content and metadata

### Slash commands

- Project settings loader: `openagentic_sdk/project/claude.py`
  - Loads `CLAUDE.md` (memory) if present
  - Indexes `.claude/commands/*.md`
- Tool: `openagentic_sdk/tools/slash_command.py`

## Runtime Loop (Sessions, Providers, Tools)

The runtime is the orchestrator:
- `openagentic_sdk/runtime.py`

### High-level flow

1) Session setup
   - Storage: `openagentic_sdk/sessions/store.py` (`FileSessionStore`)
   - Writes append-only `events.jsonl` + `meta.json`
2) Resume
   - Rebuild legacy chat messages: `openagentic_sdk/sessions/rebuild.py::rebuild_messages`
   - Rebuild Responses `input[]`: `openagentic_sdk/sessions/rebuild.py::rebuild_responses_input`
3) Model call
   - Provider protocol is detected via callable signatures (legacy vs responses)
   - Tool schemas are generated each step
4) Tool loop
   - On tool calls, runtime emits `tool.use`, runs hooks + permission gate, executes tool, then emits `tool.result`
5) Final result
   - Emits `result` event with `response_id` (when available)

### Providers

- Protocol definitions and `ModelOutput`/`ToolCall` types: `openagentic_sdk/providers/base.py`
- Responses provider: `openagentic_sdk/providers/openai_responses.py`
  - Supports both `complete()` and `stream()`
  - Handles SSE events

## Adding a New Built-in Tool

1) Implement a tool under `openagentic_sdk/tools/`:
   - Inherit `Tool`
   - Validate inputs (raise `ValueError` for bad inputs)
2) Register it in `openagentic_sdk/tools/defaults.py`
3) Ensure it has a schema/description:
   - If it is one of the built-ins in `openagentic_sdk/tools/openai.py`, add/update schema there
   - Or provide `openai_schema` on the tool instance
4) Add tests under `tests/`
5) If it touches permissions, ensure `PermissionGate` mode behavior is correct
