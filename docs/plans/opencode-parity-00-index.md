# OpenCode Parity Plan Index

This repo target: full feature parity with OpenCode.

Reference OpenCode tree: `/mnt/e/development/opencode`.

Audit snapshot: `OPENCODE_PARITY_AUDIT.md`.

## Execution Policy (Waterfall + TDD)

For each feature plan document in this series, execution follows the same loop:

1) Analysis (requirements + current behavior + parity target)
2) Plan (interfaces + data model + milestones)
3) TDD red/green (tests first, then implementation)
4) Review (self-review, risks, edge cases, security)
5) Summary (what changed, how to validate)
6) Retry until parity acceptance criteria are met

## Ordering (Dependencies)

Recommended build order (foundational first):

- 01 Prompt System + Rules (enables consistent behavior across all later features)
- 02 Config System (needed for parity-level customization)
- 03 Commands Templating (depends on config + prompt layers)
- 04 Plugins (enables extension points)
- 05 Custom Tools (often implemented via plugins/config)
- 06 MCP Full (transport + auth + registry)
- 07 LSP (IDE-grade diagnostics/search/navigation)
- 08 Compaction (context overflow + prune; needs stable prompt layers)
- 09 Sessions Advanced (undo/diff/fork/share; needs stable storage model)
- 10 Providers + Models (provider-agnostic layer + listing + auth)
- 11 Clients + Integrations (TUI/web/desktop/server/integrations)

## Plan Documents

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
