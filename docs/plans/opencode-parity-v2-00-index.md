# OpenCode Parity v2 (No-Compromise) — Index

Goal: achieve **full behavioral parity** with OpenCode (no “minimal slice”), with **equal-or-better** safety, edge-case handling, and test coverage.

This v2 plan series supersedes the earlier `docs/plans/opencode-parity-0x-*.md` “initial slice” plans by:

- Treating OpenCode as the source of truth (code + docs), not a loose inspiration.
- Specifying exact behaviors (precedence, merge semantics, templating grammar, timeouts, error cases).
- Defining acceptance criteria as executable tests (unit + contract + integration).
- Adding an explicit security model for every surface (config, plugins, tools, MCP, server).

Reference OpenCode tree (local): `/mnt/e/development/opencode`

Primary parity snapshot (this repo): `OPENCODE_PARITY_AUDIT.md`

## Execution Policy (Waterfall + TDD Loop)

For each feature area:

1) Analysis: extract OpenCode behavior (with file references)
2) Plan: design Python implementation matching behavior (APIs, data model)
3) TDD: write tests first (red)
4) Implement: make tests pass (green)
5) Review: correctness, security, edge cases, backwards compat
6) Summary: what changed + how to validate
7) Retry until parity acceptance criteria are met

## Definition of Done (Per Feature)

- Behavior parity: matches OpenCode on the documented matrix.
- Determinism: stable ordering and stable outputs.
- Security: explicit permission gating for dangerous actions; no silent network/shell/exec.
- Tests:
  - Unit tests for pure logic and parsing.
  - Contract tests for file discovery and precedence.
  - Integration tests for server endpoints / streaming where applicable.
- Diagnostics: `lsp_diagnostics` clean on modified modules.

## Dependency Order (Foundational First)

1) Prompt System + Rules (feeds everything)
2) Config System (drives discovery and behavior)
3) Commands System (templating + parts + execution)
4) Plugins + Custom Tools (extension points)
5) MCP (OAuth + prompts/resources + transports)
6) Compaction (overflow/prune/pivot)
7) Providers + Models (listing, variants, auth, headers)
8) Clients + Integrations (server API, CLI wiring, TUI)

## v2 Plan Documents

- `docs/plans/opencode-parity-v2-00-roadmap.md`
- `docs/plans/opencode-parity-v2-01-prompt-system.md`
- `docs/plans/opencode-parity-v2-02-config.md`
- `docs/plans/opencode-parity-v2-03-commands.md`
- `docs/plans/opencode-parity-v2-04-plugins-and-custom-tools.md`
- `docs/plans/opencode-parity-v2-05-mcp.md`
- `docs/plans/opencode-parity-v2-06-compaction.md`
- `docs/plans/opencode-parity-v2-07-server-and-clients.md`
- `docs/plans/opencode-parity-v2-08-providers-and-models.md`
- `docs/plans/opencode-parity-v2-09-lsp.md`
- `docs/plans/opencode-parity-v2-10-sessions.md`
- `docs/plans/opencode-parity-v2-11-integrations.md`

Re-audit snapshot:

- `docs/plans/opencode-parity-v2-90-reaudit.md`
