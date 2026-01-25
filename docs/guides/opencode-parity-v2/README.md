# OpenCode Parity v2 (User Guides)

This directory contains user-facing documentation for the OpenCode-parity features in this repo.

Audience:

- Humans using the `oa` CLI.
- Other agents/automations that need deterministic rules for configuration, commands, tools, MCP, compaction, and the local server.

## Quick Start

- One-shot prompt:

  `oa run "hello"`

- Multi-turn chat (creates/uses a session):

  `oa chat`

- Resume an existing session:

  `oa resume <session_id>`

## Guides (v2-01 .. v2-09)

- `docs/guides/opencode-parity-v2/01-prompt-system.md`
- `docs/guides/opencode-parity-v2/02-config.md`
- `docs/guides/opencode-parity-v2/03-commands.md`
- `docs/guides/opencode-parity-v2/04-plugins-and-custom-tools.md`
- `docs/guides/opencode-parity-v2/05-mcp.md`
- `docs/guides/opencode-parity-v2/06-compaction.md`
- `docs/guides/opencode-parity-v2/07-server-and-clients.md`
- `docs/guides/opencode-parity-v2/08-providers-and-models.md`
- `docs/guides/opencode-parity-v2/09-lsp.md`

## Conventions

- Config file name: `opencode.json` or `opencode.jsonc`.
- Project extension directory: `.opencode/`.
- Global config dir (XDG): `~/.config/opencode/`.
- Optional global extension dir: `~/.opencode/`.
