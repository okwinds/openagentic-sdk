# OpenCode Parity v2 — Plugins + Custom Tools

## Source of Truth (OpenCode)

- Config-driven plugin loading: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Plugin runtime: `/mnt/e/development/opencode/packages/opencode/src/plugin/*`
- Tool registry scanning: `/mnt/e/development/opencode/packages/opencode/src/tool/registry.ts`

Key behavioral details (from `tool/registry.ts`):

- Custom tool discovery uses `new Bun.Glob("{tool,tools}/*.{js,ts}")` over `await Config.directories()`.
- Each tool module is imported (top-level code executes).
- Tool IDs:
  - `namespace = basename(file, ext)`
  - each export becomes a tool:
    - export key `default` => id = `namespace`
    - named export `foo` => id = `${namespace}_${foo}`

## Current State (openagentic-sdk)

- Plugins:
  - Loader: `openagentic_sdk/plugins.py`
  - Supports `register(registry)` or `PLUGIN={hooks,tools}`
  - CLI loads `plugin/plugins` from opencode config.

- Custom tools:
  - Discovery/loader: `openagentic_sdk/custom_tools.py`
  - Scans `.opencode/{tool,tools}/*.py`, `{tool,tools}/*.py`, global `${OPENCODE_CONFIG_DIR}/{tool,tools}/*.py`

Notable gap:

- OpenCode custom tools are JS/TS modules exporting `ToolDefinition` (via `@opencode-ai/plugin`).
  Python currently only loads `*.py` tools.

## Parity Delta (No-Compromise)

OpenCode’s extension surface includes:

- They can include plugins, tools, commands, and additional dependencies.
- OpenCode runs tool code via Bun; many tools depend on `@opencode-ai/plugin`.

To reach parity in Python, we must:

- Extend custom tool discovery to include `{tool,tools}/*.{js,ts}` with the same naming rules.
- Provide an execution bridge for JS/TS tools.
- Provide an argument-schema mapping so custom tools actually surface to models (OpenAI tool schema).

Non-goals (for this batch):

- Full npm/bun dependency installation parity (OpenCode can install deps). We do not auto-install.
  If a JS tool imports third-party packages, it must be pre-installed by the user (or handled in a later step).

## Security Model

Plugins/custom tools are arbitrary code execution. Parity requires correctness, but safety must be stronger:

- Default deny for JS/TS tool loading unless explicitly enabled.
  Rationale: OpenCode imports tool modules at startup (top-level code execution), which is too risky
  to do implicitly in a Python SDK.
- Explicit provenance labels (tool origin path) carried on the tool wrapper (and included in logs).
- No implicit dependency installation; any future install flow must be permission-gated.
- Execution isolation: run JS tools in a subprocess (bun), not in-process.

Enablement (OpenAgentic-specific):

- `opencode.json`: `experimental.js_tools: true` (and/or an environment flag).
- Env override: `OA_ENABLE_JS_TOOLS=1` (CLI-only convenience).

JS/TS plugins contributing tools:

- `opencode.json`: `experimental.js_plugins: true`
- Env override: `OA_ENABLE_JS_PLUGINS=1`

## Plan

- Align discovery and naming with OpenCode:
  - scan `{tool,tools}/*.{js,ts}` under the same roots as Python custom tools
  - deterministic ordering by path, stable ordering of exports
  - map export keys to tool IDs (default vs named exports)

- Implement bun-based bridge:
  - `describe` mode: import module, enumerate exports, extract `description` + args schema
  - `execute` mode: call `def.execute(args, ctx)`
  - no network / no package installs
  - ship a minimal compatibility shim for `@opencode-ai/plugin` at runtime (sufficient for common tool patterns)

- Extend tests:
  - default-deny: JS/TS tools not loaded unless enabled
  - naming: `file.ts` => tool id `file`, `file.ts` export `foo` => `file_foo`
  - execution: simple tool returns string/dict; args defaults honored by tool module (if used)
