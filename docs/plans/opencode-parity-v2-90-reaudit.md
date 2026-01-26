# OpenCode Parity v2 — Re-Audit (Current Repo vs OpenCode)

This document is an **evidence-based delta report** comparing current `openagentic-sdk` behavior to OpenCode.

Scope: prompt system, config system, commands, plugins/tools, MCP, compaction, sessions, providers/models, server/clients.

OpenCode source-of-truth root (local): `/mnt/e/development/opencode`

Python implementation root (this repo): `openagentic_sdk/*`, `openagentic_cli/*`

## Legend

- DONE: matches OpenCode behavior closely (or intentionally exceeds while remaining compatible)
- PARTIAL: present but missing key semantics, edge cases, or surfaces
- MISSING: no equivalent implementation surface

## Executive Delta Summary

Highest-risk gaps (blockers for “no-compromise parity”):

- Commands parity is still incomplete at the **prompt parts** layer:
  - OpenCode resolves `@file` into `file://` attachments (and `@agent` into an `agent` part) via `SessionPrompt.resolvePromptParts(...)`.
  - This repo currently expands `@file` by inlining `Read`/`List` tool outputs into text in the SlashCommand renderer (different safety and token-cost profile).
- Plugins/extensions parity is incomplete:
  - OpenCode loads JS/TS plugins/tools from directory packs and installs dependencies (bun).
  - This repo can discover `.opencode/plugin/*.ts|*.js` (and records `file://...` specifiers) but cannot execute JS/TS plugins/tools.
- MCP parity is incomplete:
  - Remote transports (StreamableHTTP + SSE fallback) exist, but OpenCode’s OAuth flow parity (PKCE/state/callback server/dynamic client registration/refresh + URL-binding validation) is not implemented.
- Compaction parity is incomplete:
  - Overflow math is currently driven by `CompactionOptions.context_limit` instead of provider/model limits.
  - Prune traversal does not yet match OpenCode’s stop conditions, thresholds, and protected tools list.
- Server parity is incomplete:
  - OpenCode’s HTTP surface includes `/event` SSE plus a broad `/session/*` API (todo/status/share/revert/summarize/streaming).
  - This repo has a minimal HTTP server surface only.

Areas that are closer to parity (but still need hardening and endpoint/CLI exposure):

- Prompt system + config loader are now much closer to OpenCode behavior (provider prompt selection, headers, env block, rule discovery semantics, `config.instructions`, remote well-known config, directory-pack command/agent/mode scanning).
- Sessions have durable events + rebuild, timeline controls, fork, local share, and todo persistence.
- MCP remote transport + wrappers exist.

## 01) Prompt System + Rules

OpenCode expected behavior (key references):

- Provider prompt selection by model id patterns: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`
- Provider header injection (anthropic spoof): `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`
- Final system assembly order + Codex/OAuth special-case: `/mnt/e/development/opencode/packages/opencode/src/session/llm.ts`
- Rule discovery + `config.instructions` (files/globs/urls): `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`

Current repo status: PARTIAL

- Implemented:
  - OpenCode-style provider prompt selection by model-id patterns:
    - `openagentic_sdk/prompt_system.py` (`_opencode_provider_prompt`)
    - Embedded templates: `openagentic_sdk/opencode_prompts/*.txt`
  - Provider header injection (anthropic spoof): `openagentic_sdk/prompt_system.py` (`_opencode_header`)
  - Environment block injection (`<env>...</env>` + `<files>` stub): `openagentic_sdk/prompt_system.py` (`_opencode_environment_block`)
  - Rule discovery semantics:
    - local: `AGENTS.md` then `CLAUDE.md` then `CONTEXT.md` with early stop
    - global: first existing only
    - `openagentic_sdk/prompt_system.py` (`_custom_instruction_blocks`)
  - `config.instructions` support:
    - URL fetch (timeout 5s, failure-to-empty)
    - absolute basename glob semantics
    - relative glob-up semantics with project-discovery-disabled behavior
    - `openagentic_sdk/prompt_system.py` (`_custom_instruction_blocks`, `_resolve_relative_instruction`)
  - Codex/OAuth special-case (Responses `instructions` + system-as-user-message wiring):
    - Builder returns `(system_text, instructions)` via `BuiltSystemPrompt`
    - Runtime consumes it: `openagentic_sdk/runtime.py` (`_build_project_system_prompt` + provider call plumbing)
  - OpenAgentic `.claude` compatibility remains additive:
    - `openagentic_sdk/project/claude.py`
    - `openagentic_sdk/prompt_system.py` (`_claude_project_blocks`)

- Missing vs OpenCode:
  - Exact prompt assembly semantics differ in details:
    - OpenCode maintains a 2-part `system[]` structure for caching when header is unchanged (see `/mnt/e/development/opencode/packages/opencode/src/session/llm.ts`).
    - This repo currently emits a single `system_text` string, joined with `\n\n` between blocks.
  - OpenCode supports `input.system` and `input.user.system` separately (last-user system has highest precedence). This repo currently has only `OpenAgenticOptions.system_prompt` as a programmatic override.
  - Tests still missing for URL-instruction fetch failure modes and timeout behavior (implementation exists).

## 02) Config System

OpenCode expected behavior (key references):

- Precedence layers (well-known -> global -> OPENCODE_CONFIG -> project -> OPENCODE_CONFIG_CONTENT -> directory packs):
  - `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Merge semantics: only `plugin[]` and `instructions[]` concat+dedupe; others follow default deep-merge behavior.
- Substitutions:
  - `{env:VAR}`
  - `{file:path}` resolves relative to config file dir, supports `~/`, errors on missing, escapes for JSON string literal, skips commented-out tokens.
- `$schema` insertion and optional write-back.

Current repo status: PARTIAL

- Implemented (close to parity):
  - Precedence layers:
    - remote well-known config from auth entries (type `wellknown`): `openagentic_sdk/opencode_config.py` (`load_state`, `/_fetch_json`)
    - global config in XDG config dir: `openagentic_sdk/opencode_config.py` (`_xdg_config_dir`, `_load_global_config`)
    - `OPENCODE_CONFIG` file override: `openagentic_sdk/opencode_config.py` (`load_state`)
    - project config discovery (up-tree): `openagentic_sdk/opencode_config.py` (`_find_up` + load order)
    - inline config via `OPENCODE_CONFIG_CONTENT`: `openagentic_sdk/opencode_config.py` (`_parse_inline_json`)
    - directory-pack scanning: `.opencode` up-tree + `~/.opencode` + `OPENCODE_CONFIG_DIR`: `openagentic_sdk/opencode_config.py` (`load_state`)
  - Merge semantics:
    - deep merge objects
    - concat+dedupe only for `plugin` and `instructions`
    - OpenCode-style canonical plugin name dedupe (later wins)
    - `openagentic_sdk/opencode_config.py` (`_merge_config_concat_arrays` + plugin canonicalization)
  - JSONC parsing + error reporting:
    - comment stripping and trailing comma handling
    - error messages include line/column + failing line
    - `openagentic_sdk/opencode_config.py` (`_strip_jsonc_comments` + `_strip_trailing_commas` + parse error assembly)
  - Substitutions on the raw JSONC text (parity behavior):
    - `{env:VAR}` expansion
    - `{file:path}` expansion with:
      - relative-to-config-dir resolution
      - `~/` expansion
      - missing-file errors
      - commented-line skip
      - JSON string-literal escaping (newline/quotes)
    - `openagentic_sdk/opencode_config.py` (`_apply_text_substitutions`)
  - `$schema` insertion and write-back attempt: `openagentic_sdk/opencode_config.py` (`load_config_file`)
  - Directory-pack loaders:
    - markdown commands: `{command,commands}/**/*.md`
    - markdown agents: `{agent,agents}/**/*.md`
    - markdown modes: `{mode,modes}/*.md`
    - plugin discovery: `{plugin,plugins}/*.{js,ts}` -> stored as `file://...`
    - `openagentic_sdk/opencode_config.py` (`_load_commands_from_dir`, `_load_agents_from_dir`, `_load_modes_from_dir`, `_load_plugins_from_dir`)

- Missing vs OpenCode:
  - Dependency installation for directory packs (bun + `@opencode-ai/plugin`) is not implemented (and must be permission-gated).
  - Remote well-known config fetch behavior differs:
    - OpenCode throws on non-OK fetch in `Config.state`.
    - This repo treats fetch failures as “empty” (safer default, but not strict parity).

## 03) Commands (Templates + Parts + Execution)

OpenCode expected behavior (key references):

- Registry sources (built-ins + config commands + markdown commands + MCP prompts):
  - `/mnt/e/development/opencode/packages/opencode/src/command/index.ts`
  - `/mnt/e/development/opencode/packages/opencode/src/config/config.ts` (`{command,commands}/**/*.md`)
- Runtime expansion:
  - args tokenization (quoted strings, `[Image N]`), `$N` with max-placeholder swallowing remainder, `$ARGUMENTS` (multiline), implicit arg appending
  - shell: `!`cmd`` (concurrent)
  - `@file` -> attachment parts (file/dir mime), fallback `@name` -> agent part
  - `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts`
- `@file` parsing regex edge cases:
  - `/mnt/e/development/opencode/packages/opencode/src/config/markdown.ts`
  - `/mnt/e/development/opencode/packages/opencode/test/config/markdown.test.ts`

Current repo status: PARTIAL

 Implemented (closer to OpenCode, but not identical model):
  - Command template resolution with precedence:
    - config-defined commands + directory-pack command entries
    - `.opencode/commands/<name>.md`
    - `.claude/commands/<name>.md` (compat)
    - global `~/.config/opencode/commands/<name>.md`
    - built-ins `init`/`review`
    - `openagentic_sdk/commands.py`
    - embedded built-ins: `openagentic_sdk/opencode_commands/initialize.txt`, `openagentic_sdk/opencode_commands/review.txt`
  - Args tokenization + placeholder semantics matching OpenCode:
    - `argsRegex` behavior (quoted args + `[Image N]`)
    - `$N` replacement with “max index swallows remainder”
    - `$ARGUMENTS` replacement + implicit append
    - `openagentic_sdk/runtime.py` (`_expand_command_args`)
  - Shell expansion syntax matches OpenCode (`!`cmd``) and executes concurrently:
    - permission-gated via `PermissionGate`
    - `openagentic_sdk/runtime.py` (`bash_regex` + `asyncio.gather`)
  - `@...` parsing uses OpenCode’s regex shape and dedupes refs:
    - `openagentic_sdk/runtime.py` (`file_regex = r"(?<![\w`])@(... )"`)

- Missing / incorrect vs OpenCode:
  - Prompt parts are still text-based, not attachment-based:
    - OpenCode: `resolvePromptParts()` converts `@file` into `file://...` parts with mime (and model-message conversion strips text/plain and directory files to text).
    - Here: `@file` is expanded by calling `Read`/`List` tools and appending their outputs into the rendered text.
  - `@agent` fallback is not a first-class `agent` part; it is appended as a synthetic instruction string.
  - MCP prompts are exposed as tools (wrappers) but not yet integrated into the slash-command registry.
  - `openagentic_sdk/tools/slash_command.py` still loads `.claude/commands/<name>.md` only; parity behavior lives in the runtime tool-loop path.

## 04) Plugins + Custom Tools

OpenCode expected behavior (key references):

- `.opencode` directory packs (commands/agents/modes/plugins/tools) loaded from `Config.directories()`:
  - `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Plugins are JS/TS modules and OpenCode installs dependencies for `.opencode` directories (bun).

Current repo status: PARTIAL

- Implemented:
  - Python plugin loader for explicit specs: `openagentic_sdk/plugins.py`
  - Reads plugin list from config: `plugins_from_opencode_config()` in `openagentic_sdk/plugins.py`
  - Python custom tool discovery in `.opencode/{tool,tools}`, project `{tool,tools}`, and `~/.config/opencode/{tool,tools}`: `openagentic_sdk/custom_tools.py`
  - Directory-pack scanning for plugin specifiers (JS/TS file URLs) and markdown commands/agents/modes:
    - `openagentic_sdk/opencode_config.py` (`_load_plugins_from_dir`, `_load_commands_from_dir`, `_load_agents_from_dir`, `_load_modes_from_dir`)

- Missing vs OpenCode:
  - JS/TS plugin execution parity:
    - OpenCode can execute plugin/tool modules authored against `@opencode-ai/plugin`.
    - This repo does not execute JS/TS plugins/tools; only Python plugins/tools run.
  - Dependency install parity for directory packs is missing.
  - Security posture is still incomplete for a “no-compromise” mode:
    - auto-loading untrusted extension code should be explicit opt-in with provenance and strong permission gating.

## 05) MCP

OpenCode expected behavior (key references):

- OAuth (PKCE + local callback + client registration + refresh + URL-bound credentials):
  - `/mnt/e/development/opencode/packages/opencode/src/mcp/oauth-provider.ts`
  - `/mnt/e/development/opencode/packages/opencode/src/mcp/auth.ts` (0600 file perms)
- Prompts/resources parity:
  - surfaced in registry, integrated into commands/resources.

Current repo status: PARTIAL

- Implemented:
  - Remote MCP client: StreamableHTTP probe then SSE fallback: `openagentic_sdk/mcp/remote_client.py`
  - Bearer token store + header merge: `openagentic_sdk/mcp/credentials.py` (`McpCredentialStore.merged_headers`)
  - Tool wrappers for tools/prompts/resources (as tools): `openagentic_sdk/mcp/wrappers.py`
  - CLI: `oa mcp list/auth/logout`: `openagentic_cli/mcp_cmd.py`, `openagentic_cli/args.py`
  - Tool-loop wiring registers MCP tools/prompts/resources at runtime:
    - `openagentic_sdk/runtime.py` (registers wrappers on query start)
  - Transport coverage tests exist:
    - SSE fallback: `tests/test_mcp_remote_sse_tools.py`
    - StreamableHTTP: `tests/test_mcp_remote_tools.py`
    - stdio MCP: `tests/test_mcp_local_tools.py`

- Missing vs OpenCode:
  - OAuth flow (callback server, PKCE verifier, state, refresh tokens, dynamic registration).
  - URL binding validation for stored credentials.
  - Secure file permissions for MCP creds store are not parity-level:
    - OpenCode: writes `mcp-auth.json` with `chmod 0600` and tracks `serverUrl` for URL binding.
      - `/mnt/e/development/opencode/packages/opencode/src/mcp/auth.ts`
    - This repo: `openagentic_sdk/mcp/credentials.py` writes `credentials.json` without enforcing `0600`.
    - Note: general provider auth store here does set `0600`: `openagentic_sdk/auth.py`.
  - Prompts-as-commands integration.

## 06) Compaction

OpenCode expected behavior (key references):

- Overflow math uses model limits + OUTPUT_TOKEN_MAX; auto enabled by default.
- Prune algorithm:
  - protects newest user turn (requires 2 user turns before pruning)
  - stops at summary pivot
  - stops at first already-compacted tool output (idempotence boundary)
  - protects tool `skill`
  - applies only if prunedTokens > 20k
- Hard compaction:
  - queues compaction marker and produces summary assistant message
  - compaction marker question: `What did we do so far?`
  - plugin hook `experimental.session.compacting`
  - auto-continue synthetic user message

References:

- `/mnt/e/development/opencode/packages/opencode/src/session/compaction.ts`
- `/mnt/e/development/opencode/packages/opencode/src/session/message-v2.ts` (placeholder + pivot filter)

Current repo status: PARTIAL

- Implemented:
  - Summary pivot (assistant message `is_summary=True`) and tool-output placeholder event: `openagentic_sdk/compaction.py`, `openagentic_sdk/runtime.py`, `openagentic_sdk/sessions/rebuild.py`
  - Placeholder string matches OpenCode: `[Old tool result content cleared]`
  - Compaction marker question matches OpenCode: `openagentic_sdk/compaction.py` (`COMPACTION_MARKER_QUESTION`)
  - Auto-continue message matches OpenCode: `openagentic_sdk/runtime.py` (inserts user text `Continue if you have next steps`)
  - Some pruning mechanics already exist (idempotence boundary via `ToolOutputCompacted` events): `openagentic_sdk/compaction.py` (`select_tool_outputs_to_prune`)

- Missing / incorrect vs OpenCode:
  - Overflow math uses `CompactionOptions.context_limit` (default 0 => disabled) rather than provider/model token limits; output reserve differs.
  - Pruning traversal semantics differ:
    - no 2-user-turn guard
    - no protected tools list (e.g. `skill`)
    - token thresholds differ (`PRUNE_MINIMUM=20_000`, `PRUNE_PROTECT=40_000` in OpenCode)
    - stop boundary differs (OpenCode stops at summary + first already-compacted tool output; this repo filters by latest summary pivot events only)
  - No plugin hook equivalent to `experimental.session.compacting`.
  - Compaction prompt/context hook parity is missing (OpenCode uses `Plugin.trigger("experimental.session.compacting", ...)`).

## 07) Sessions (Timeline / Fork / Share / Todo)

OpenCode expected behavior includes:

- append-only sessions with summary pivots
- todo list per session
- session fork / children
- share/unshare
- revert/diff/snapshots (worktree)

Current repo status: PARTIAL

- Implemented:
  - Event log + rebuild.
  - Timeline controls: checkpoint/set_head/undo/redo.
  - Fork metadata.
  - Local share provider.
  - Todo persistence to `todos.json` on `TodoWrite`.
  - Worktree diff helpers exist (not git-snapshot parity): `openagentic_sdk/sessions/diff.py`

- Missing vs OpenCode:
  - Worktree snapshot/revert system (OpenCode has Snapshot/Revert subsystems).
  - Revert cleanup semantics that delete messages/parts after a revert boundary.
  - Server endpoints for session status/children/todo/share/revert/summarize and `/event` SSE parity.

## 08) Providers + Models

OpenCode expected behavior includes:

- Provider auth store + flows (including OpenAI OAuth special-case)
- Model listing + metadata (limits, variants) used by compaction
- Provider/model prompt integration

Current repo status: PARTIAL

- Implemented:
  - Provider registry and adapter aliases: `openagentic_sdk/providers/*`
  - Config parsing for provider.models + variants: `openagentic_sdk/providers/registry.py`, `openagentic_cli/config.py`
  - Provider/model prompt integration exists in the prompt system (selection by model id patterns): `openagentic_sdk/prompt_system.py`
  - Local auth store exists with `0600` permissions:
    - `openagentic_sdk/auth.py` supports `api`, `oauth`, and `wellknown`

- Missing vs OpenCode:
  - models.dev integration or equivalent authoritative model metadata.
  - Provider auth store parity (beyond API key env/flags) and OAuth flows.
  - Model limit propagation into compaction math.
  - Full provider/server OAuth surface parity (`/provider/:providerID/oauth/*` endpoints).

## 09) Server + Clients (CLI/TUI)

OpenCode expected server surface (selected routes):

- `/session` list with filters, `/session/status`, `/session/:id`, `/session/:id/children`, `/session/:id/todo`, create/update/delete, streaming message endpoints, summarize endpoints, etc.

Reference: `/mnt/e/development/opencode/packages/opencode/src/server/routes/session.ts`

Current repo status: MISSING (product parity) / PARTIAL (SDK surface)

- Implemented (minimal SDK surface only):
  - `openagentic_sdk/server/http_server.py` and `openagentic_sdk/server/http_client.py`
  - Basic contract test exists: `tests/test_http_server_surface.py`

- Missing vs OpenCode:
  - Most routes and semantics.
  - Streaming parity:
    - OpenCode has `/event` SSE bus stream and streaming message endpoints under `/session/:sessionID/message`.
    - This repo has no `/event` SSE equivalent.
  - Auth/token protection and request size limits.
  - `oa serve` / `oa tui` CLI exposure.

## 10) LSP

OpenCode expected behavior (key references):

- LSP orchestration: `/mnt/e/development/opencode/packages/opencode/src/lsp/index.ts`
- Server registry + root detection: `/mnt/e/development/opencode/packages/opencode/src/lsp/server.ts`
- Tool wrapper: `/mnt/e/development/opencode/packages/opencode/src/tool/lsp.ts`

Current repo status: PARTIAL

- Implemented:
  - Minimal stdio JSON-RPC LSP client + manager:
    - `openagentic_sdk/lsp/client.py`
    - `openagentic_sdk/lsp/manager.py`
  - Tool surface:
    - `openagentic_sdk/tools/lsp.py`
  - Stub-server tests:
    - `tests/fixtures/lsp_stub_server.py`
    - `tests/test_lsp_tool.py`

- Missing vs OpenCode:
  - Built-in server registry parity and config override semantics.
  - Client caching per (root, serverID), broken-server backoff.
  - Document lifecycle notifications (`didOpen`, `didChange`, watched files) and diagnostics debounce/wait semantics.

## 11) Integrations

OpenCode expected behavior (present in this checkout):

- ACP integration:
  - `/mnt/e/development/opencode/packages/opencode/src/acp/*`
  - ACP tests: `/mnt/e/development/opencode/packages/opencode/test/acp/*.test.ts`
- GitHub Action integration:
  - `/mnt/e/development/opencode/github/*`

Current repo status: MISSING / STUB

- Present only as lightweight stubs:
  - `openagentic_sdk/integrations/*`

## CLI Surface Snapshot

Current `oa` commands are limited to: `chat`, `run`, `resume`, `logs`, `mcp`, `share`, `unshare`, `shared`.

Reference: `openagentic_cli/args.py`, `openagentic_cli/__main__.py`

OpenCode includes a much broader CLI/TUI surface; we need parity commands to manage server, sessions, config, providers/auth, MCP OAuth, etc.

## Cross-Cutting Security Gaps

For “no-compromise parity”, security must be explicit and testable:

- Config substitution and errors must not leak secrets.
- Remote config/instruction fetching must be opt-in, bounded, and auditable.
- Plugin/tool loading is arbitrary code execution and must be gated.
- Server must enforce auth, size limits, and input validation.
- Credential stores must set strict file permissions and avoid logging secrets.

Notes / references worth encoding into hardened-mode acceptance criteria:

- MCP OAuth + transport specs (authoritative):
  - https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
  - https://modelcontextprotocol.io/specification/2025-03-26/basic/transports
  - https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices
- OAuth security baseline for native-app flows:
  - PKCE: https://datatracker.ietf.org/doc/html/rfc7636
  - Loopback redirect URIs (native apps): https://datatracker.ietf.org/doc/html/rfc8252
  - OAuth Security BCP: https://www.rfc-editor.org/rfc/rfc9700
