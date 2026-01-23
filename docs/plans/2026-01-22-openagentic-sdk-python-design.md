# Open Agent SDK (Python) — Design (v0)

## Goal

Build an open-source “Agent SDK” in **pure Python** that is **API/behavior-compatible in spirit** with the Claude Agent SDK (CAS) programming model (streaming `query()`, tool execution, sessions, hooks), but:

- Does **not** depend on the closed-source Claude Code CLI.
- Does **not** require running or installing `opencode` at runtime.
- May **reuse concepts** and selectively **port implementation ideas** from this repo.

Priority: strong built-in capability (tools + approvals + skills) and a provider-agnostic model layer (with **OpenAI implemented first**).

Non-goals for v1:

- MCP execution (leave **API + docs placeholders**; implement later).
- Perfect 1:1 type names with CAS (e.g., `OpenAgentOptions` instead of `ClaudeAgentOptions`).

## Location (monorepo incubation)

Add a new package at:

- `packages/sdk/openagentic-sdk/` (pure Python project)

This keeps incubation close to existing agent/runtime work and matches the repo’s SDK layout, while remaining runtime-independent.

## High-level Architecture

Layered design to keep concerns separable:

1. **Runtime**
   - The agent loop: call provider, interpret tool calls, run tools, feed results back, stop.
   - Emits an **async event stream** and writes the same events to session storage.
2. **Providers**
   - Vendor adapters: OpenAI (first), then others via a shared interface.
   - Responsibilities: message formatting, streaming parsing, tool-calling mapping, usage stats.
3. **Tools**
   - Built-in tool implementations + a registry.
   - Tools run under approvals and hook interception.
4. **Permissions**
   - Approval callback + optional interactive terminal approver.
   - Uniform gating for all tool invocations.
5. **Hooks**
   - Lifecycle callbacks that can audit, block, or rewrite tool/model IO.
6. **Project settings**
   - `.claude` compatibility: memory, skills, slash commands.
7. **Sessions**
   - Default filesystem persistence with `resume` and subagent linkage.

## Public API (Python)

Two entry points:

### `query()`: streaming

```py
async for event in query(
    prompt="Find and fix the bug in auth.py",
    options=OpenAgentOptions(
        provider="openai",
        model="gpt-4.1-mini",
        allowed_tools=["Read", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="prompt",  # or callback-based
        setting_sources=["project"],
    ),
):
    ...
```

### `run()`: one-shot

Consumes `query()` internally and returns a single object with the final output + full event list.

## Event Model

Events are versioned, JSON-serializable (for `events.jsonl`) and ergonomic as Python classes.

Minimum event types:

- `SystemInit(session_id, cwd, sdk_version, options_summary, enabled_tools, enabled_providers)`
- `AssistantDelta(text_delta, ...)` (optional but recommended for streaming UX)
- `AssistantMessage(text, ...)` (final for a given turn)
- `ToolUse(tool_use_id, name, input, parent_tool_use_id?, agent_name?)`
- `ToolResult(tool_use_id, output, is_error, error_type?, error_message?)`
- `HookEvent(hook_point, name, matched, duration_ms, action)`
- `Result(final_text, usage, stop_reason, steps, session_id)`

Subagent events include `parent_tool_use_id` to associate with the triggering `Task` tool call.

## Options (`OpenAgentOptions`)

Representative fields:

- Provider/model:
  - `provider: str` (e.g., `"openai"`)
  - `model: str`
  - `api_key: str | None` (or provider-specific config objects)
- Execution:
  - `max_steps: int`
  - `timeout_s: float | None`
  - `resume: str | None` (session id)
  - `fork: str | None` (optional future)
  - `cwd: str | None`, `project_dir: str | None`
- Tools:
  - `allowed_tools: list[str] | None` (whitelist)
  - `tool_config: dict` (per-tool config; e.g., web limits)
- Permissions:
  - `permission_mode: Literal["prompt","callback","bypass","deny"]` (exact names TBD)
  - `approver: Callable[[ToolUseRequest, Context], Awaitable[Approval]] | None`
  - `interactive_approver: bool` (enables a built-in terminal approver)
- Hooks:
  - `hooks: dict[HookPoint, list[HookMatcher]]`
  - `enable_message_rewrite_hooks: bool` (default false)
- Project config:
  - `setting_sources: list[Literal["project"]] | None`
  - `.claude` paths inferred from `project_dir`/`cwd`
- Subagents:
  - `agents: dict[str, AgentDefinition] | None`

## Built-in Tools (v1)

Goal: strong baseline so skills are actually executable.

Core:

- `Read` / `Write` / `Edit`
- `Glob` / `Grep`
- `Bash`

Web:

- `WebFetch`
- `WebSearch` (Tavily backend first; requires config and approval)

Interaction:

- `AskUserQuestion` (used for approvals and clarifying questions)
- `Task` (subagents)

Notes:

- All tool inputs/outputs are schema’d and recorded to `events.jsonl`.
- Output size limits + truncation should be configurable per tool.

## Permissions / Approvals

Dual-mode:

1. **Callback approver**: host application supplies `approver(...)`.
2. **Interactive approver**: SDK can prompt in terminal (opt-in).

Default posture should be conservative for “dangerous” tools (`Bash`, `WebFetch`, `WebSearch`, `Edit`, `Write`), but the exact default policy is a product decision.

## `.claude` Compatibility

Support CAS-like project configuration when `setting_sources=["project"]`:

- Memory: `CLAUDE.md` or `.claude/CLAUDE.md`
- Skills: `.claude/skills/**/SKILL.md`
- Slash commands: `.claude/commands/*.md`

Loading strategy:

- Index and expose **names + descriptions**, but don’t eagerly inject full contents.
- Agents use `Read` to open skill markdown when needed.

Slash commands execute as an **agent-callable capability** (not preprocessor):

- Provide a tool like `SlashCommand(name, args)` that reads and returns the command content/template.

## Sessions (filesystem persistence, required)

Default store: filesystem under a user directory (XDG/Windows/macOS conventions).

Structure:

- `<base>/sessions/<session_id>/meta.json`
- `<base>/sessions/<session_id>/events.jsonl` (append-only)
- Optional: `<base>/sessions/<session_id>/context.json` (summaries/caches)

`resume=session_id` restores from persisted events and continues.

## Subagents (`Task` tool, required)

Implement `Task` as a built-in tool that spawns a child `AgentRuntime` using asyncio:

- Child has its own short-term context, but inherits (or tightens) tool permissions and hooks.
- Child events carry `parent_tool_use_id` and can be streamed through the parent.
- Persist both:
  - Parent session records child events with `parent_tool_use_id`.
  - Optionally store child session separately for independent `resume`.

## Providers (OpenAI first)

Provider interface must support:

- Streaming assistant output.
- Tool calling → SDK `ToolUse` events.
- Usage stats mapping.

V1 ordering:

1. OpenAI
2. Add more providers behind the same adapter layer.

## MCP (v1 placeholder)

No implementation in v1, but reserve:

- `OpenAgentOptions.mcp_servers` / `mcp_registry` fields.
- A `MCP` section in docs that explains planned transport support (stdio/HTTP/SSE), auth, and tool surface.

## Testing Strategy

Start with unit tests for:

- Event serialization/deserialization.
- Permission gating logic.
- Hook matching + rewrite/block behavior.
- Tool correctness for small fixtures (Read/Edit/Glob/Grep).
- Provider “contract tests” using recorded fixtures/mocks (avoid real network in CI by default).

## Next Step

Create an implementation plan (phased milestones), then scaffold `packages/sdk/openagentic-sdk/` with:

- `pyproject.toml` (packaging + deps)
- core modules: `query/run`, events, providers(openai), tool registry, permissions, sessions(file store), hooks
- minimal docs and examples

