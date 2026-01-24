# OpenCode Parity Audit (openagentic-sdk)

This document records the current, evidence-based gap analysis between:

- OpenCode source tree: `/mnt/e/development/opencode`
- This repo: `/mnt/e/development/openagentic-sdk`

Goal: full feature parity with OpenCode ("complete alignment").

Note: this file is a snapshot of findings. Implementation plans live in `docs/plans/opencode-parity-*.md`.

## Current Baseline (Already Implemented Here)

### Runtime + Sessions

- Multi-turn agent runtime with real tool loop: `openagentic_sdk/runtime.py`
- Persistent sessions (events + meta) and resume reconstruction:
  - `openagentic_sdk/sessions/store.py`
  - `openagentic_sdk/sessions/rebuild.py`
- Public APIs:
  - Streaming: `openagentic_sdk/api.py` (`query()`)
  - One-shot: `openagentic_sdk/api.py` (`run()`)
  - CAS-style: `openagentic_sdk/message_query.py` (`query_messages()`)

### Providers

- OpenAI Responses protocol provider:
  - `openagentic_sdk/providers/openai_responses.py`
- OpenAI-compatible provider with custom base_url/headers:
  - `openagentic_sdk/providers/openai_compatible.py`

### Built-in Tools + Permissions

- Default tool registry: `openagentic_sdk/tools/defaults.py`
- Permission gating modes: `openagentic_sdk/permissions/gate.py`
- Tool prompt templates ("opencode-style" long descriptions): `openagentic_sdk/tool_prompts/*.txt`

### .claude Compatibility (Partial)

- Project system prompt injection from `CLAUDE.md` / `.claude/CLAUDE.md` plus `.claude/commands/*.md` index:
  - `openagentic_sdk/project/claude.py`
  - `openagentic_sdk/runtime.py`
- SlashCommand tool loads `.claude/commands/<name>.md`:
  - `openagentic_sdk/tools/slash_command.py`
- Skills on disk (project + global), exposed via `Skill` tool description:
  - `openagentic_sdk/skills/index.py`
  - `openagentic_sdk/tools/skill.py`

### Subagents

- Programmatic subagents via `OpenAgenticOptions.agents` and runtime-managed `Task` tool:
  - `openagentic_sdk/options.py`
  - `openagentic_sdk/runtime.py`

## Major Gaps vs OpenCode (What Must Be Built)

This section lists missing OpenCode feature areas with "source of truth" locations in OpenCode for parity reference.

### 1) Prompt Architecture / Prompt Management (Major)

OpenCode uses a layered, configurable prompt system:

- Provider/model-specific system/header prompts (templates + selection logic):
  - Templates: `opencode/packages/opencode/src/session/prompt/*.txt`
  - Selection/injection: `opencode/packages/opencode/src/session/system.ts`
- Agent-specific prompts (plan/build/explore/summary/title/compaction):
  - `opencode/packages/opencode/src/agent/prompt/*.txt`
  - `opencode/packages/opencode/src/agent/agent.ts`
- Project/global rules loading (AGENTS.md, CLAUDE.md, CONTEXT.md, etc) + config-driven `instructions[]`:
  - `opencode/packages/opencode/src/session/system.ts`
  - `opencode/packages/opencode/src/config/config.ts`

Current repo status:

- System prompt is mostly `.claude` memory + optional CLI hook injection.
- No first-class system prompt layering API surface in `OpenAgenticOptions`.
- No OpenCode-style "instructions[]" loader (URL/glob/file) and no AGENTS.md semantics.

### 2) Config System (Major)

OpenCode config precedence + merging + substitutions:

- `opencode/packages/opencode/src/config/config.ts`
- Docs: `opencode/packages/web/src/content/docs/config.mdx`

Current repo status:

- No `opencode.json{,c}`-like loader; configuration is mostly `OpenAgenticOptions` + env.

### 3) Commands System (Prompt Presets + Templating) (Major)

OpenCode commands support templated prompts, args, `!cmd`, `@files`, etc:

- Command registry: `opencode/packages/opencode/src/command/index.ts`
- Docs: `opencode/packages/web/src/content/docs/commands.mdx`

Current repo status:

- `SlashCommand` only loads a static `.claude/commands/<name>.md` file.
- No templating/arguments/command sources beyond `.claude`.

### 4) Plugins + Custom Tools (Major)

OpenCode supports plugins and on-disk custom tools discovery:

- Plugins: `opencode/packages/opencode/src/plugin/*` + loader in `opencode/packages/opencode/src/config/config.ts`
- Custom tools scanning: `opencode/packages/opencode/src/tool/registry.ts`

Current repo status:

- Hooks exist (`openagentic_sdk/hooks/engine.py`) but no plugin packaging/loading.
- No dynamic disk-scanned tools.

### 5) MCP (Major; current repo is partial)

OpenCode has MCP local/remote transports + OAuth + CLI management:

- MCP client/registry: `opencode/packages/opencode/src/mcp/index.ts`
- OAuth flows: `opencode/packages/opencode/src/mcp/oauth-provider.ts`
- CLI: `opencode/packages/opencode/src/cli/cmd/mcp.ts`

Current repo status:

- Only "SDK-defined MCP tools" wrapper exists (in-process wrapper): `openagentic_sdk/mcp/sdk.py`.
- `OpenAgenticOptions` labels MCP as placeholders beyond that: `openagentic_sdk/options.py`.

### 6) LSP Integration (Major)

OpenCode provides LSP server lifecycle + status endpoint + optional tool integration:

- LSP: `opencode/packages/opencode/src/lsp/*`

Current repo status:

- No Python LSP integration.

### 7) Compaction / Context Overflow Handling (Major; documented only here)

OpenCode implements compaction and tool-output pruning:

- Implementation: `opencode/packages/opencode/src/session/compaction.ts`
- Design doc: `opencode/COMPACTION.md`

Current repo status:

- Design doc exists: `COMPACTION.md`
- No runtime implementation found under `openagentic_sdk/`.

### 8) Advanced Session Features (Major)

OpenCode supports richer session lifecycle:

- Revert/undo via snapshots: `opencode/packages/opencode/src/session/revert.ts`
- Summary/status/timeline helpers: `opencode/packages/opencode/src/session/summary.ts`, `opencode/packages/opencode/src/session/status.ts`
- Share/unshare: `opencode/packages/opencode/src/share/share-next.ts`
- Server session routes: `opencode/packages/opencode/src/server/routes/session.ts`

Current repo status:

- Only durable logs + resume exist; no snapshot-based undo/diff/fork/share.

### 9) Provider Coverage + Model Listing (Major)

OpenCode is provider-agnostic (Models.dev + AI SDK) with listing/variants/auth management.

- Provider stack: `opencode/packages/opencode/src/provider/*`

Current repo status:

- OpenAI Responses + OpenAI-compatible only.

### 10) Clients + Integrations (Product-Level)

OpenCode includes multiple product clients and integrations:

- TUI + server + web + desktop: `opencode/packages/opencode/src/cli/cmd/tui/*`, `opencode/packages/opencode/src/server/*`, `opencode/packages/desktop/*`
- GitHub Action agent: `opencode/github/README.md`
- VS Code extension: `opencode/sdks/vscode/README.md`
- Slack bot: `opencode/packages/slack/README.md`
- ACP (Zed): `opencode/packages/opencode/src/acp/README.md`

Current repo status:

- This repo is primarily a Python SDK + `oa` CLI. Parity here implies implementing comparable optional components or compatible surfaces.

## Notes / Scope Clarifications (for parity work)

- This repo contains a separate TypeScript `tool/` tree (e.g. `tool/lsp.ts`), but the Python runtime does not import it. For parity, we will implement required behavior in the Python runtime unless explicitly deciding to embed/bridge the TS toolchain.

## Implementation Roadmap

See:

- `docs/plans/opencode-parity-00-index.md`
- `docs/plans/opencode-parity-01-prompt-system-and-rules.md`
- `docs/plans/opencode-parity-02-config-system.md`
- `docs/plans/opencode-parity-03-commands-templating.md`
- `docs/plans/opencode-parity-04-plugins.md`
- `docs/plans/opencode-parity-05-custom-tools.md`
- `docs/plans/opencode-parity-06-mcp-full.md`
- `docs/plans/opencode-parity-07-lsp.md`
- `docs/plans/opencode-parity-08-compaction.md`
- `docs/plans/opencode-parity-09-sessions-advanced.md`
- `docs/plans/opencode-parity-10-providers-and-models.md`
- `docs/plans/opencode-parity-11-clients-and-integrations.md`
