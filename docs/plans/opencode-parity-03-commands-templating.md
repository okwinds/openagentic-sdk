# Parity 03: Commands (Prompt Presets + Template Engine)

Status: implemented (initial slice) in this repo:

- SlashCommand now supports opencode-compatible command roots and templating:
  - discovery: config-defined commands + `.opencode/commands` + `.claude/commands` + global `~/.config/opencode/commands`
  - template expansions: `$ARGUMENTS`, `$1..$20`, `@file` include, inline `!shell`
- Runtime handles `SlashCommand` as a special-cased tool to return rendered `content`.
- Tests

Key files:

- `openagentic_sdk/commands.py`
- `openagentic_sdk/runtime.py`
- `openagentic_sdk/tools/openai.py`
- `tests/test_slash_command_templating.py`

## Analysis

OpenCode commands are configurable prompt presets with templating:

- Sources: built-ins + on-disk commands + config-defined commands + MCP prompts.
- Template features: `$ARGUMENTS`, `$1..$n`, `!` shell expansion, `@file` references.

References:

- `opencode/packages/opencode/src/command/index.ts`
- Docs: `opencode/packages/web/src/content/docs/commands.mdx`

Current repo: `.claude/commands/*.md` loaded by `SlashCommand` tool only.

## Plan

- Add a command registry abstraction:
  - built-in commands (parity set)
  - `.opencode/commands/*.md` and global commands
  - config-defined commands
  - MCP-provided prompts (later)
- Implement template evaluation (safe subset first), with explicit security constraints.
- Extend `SlashCommand` tool to run through registry, not only `.claude`.

## TDD

- Tests for argument expansion, file reference resolution, and denied shell execution when disallowed.
