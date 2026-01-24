# Parity 11: Clients + Integrations (Product-Level Surfaces)

## Analysis

OpenCode includes:

- TUI, server, web UI, desktop.
- GitHub Action, VS Code extension, Slack bot, ACP.

References:

- TUI: `opencode/packages/opencode/src/cli/cmd/tui/*`
- Server: `opencode/packages/opencode/src/server/*`
- Web: `opencode/packages/opencode/src/cli/cmd/web.ts`
- GitHub: `opencode/github/README.md`
- VSCode: `opencode/sdks/vscode/README.md`
- Slack: `opencode/packages/slack/README.md`
- ACP: `opencode/packages/opencode/src/acp/README.md`

Current repo ships a Python SDK + `oa` CLI.

## Plan

- Implement comparable surfaces as optional packages/modules:
  - HTTP server exposing session routes
  - TUI client (Python) or compatible UI layer
  - Integration adapters (GitHub/Slack/VSCode)
- Keep SDK core independent; integrations live behind optional dependencies.

## TDD

- Contract tests against server endpoints; integration tests for bots/actions.
