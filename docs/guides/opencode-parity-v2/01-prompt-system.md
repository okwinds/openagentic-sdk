# v2-01 Prompt System + Rules

This guide explains how system prompts and rules are assembled (OpenCode-style), and where to put rule files.

## What Gets Sent To The Model

At runtime, the SDK builds a "system prompt" made of multiple blocks (joined by blank lines):

- Provider header (optional)
- Provider/base prompt (depends on model)
- Environment block (cwd, platform, date/time)
- Custom rules/instructions (local rule files + global rule files)
- Config-driven `instructions[]` (files/globs/URLs)
- Optional explicit override from code/CLI

Special case (Codex/OpenAI OAuth style):

- The Responses API `instructions` field is used.
- The joined system content may be sent as a `role: user` message (OpenCode behavior).

## Rule Files (Local Project)

The loader searches upward from your working directory for rule files.

Local rule file kinds (checked in this priority order):

1) `AGENTS.md`
2) `CLAUDE.md`
3) `CONTEXT.md` (deprecated)

Important: once it finds a rule-file kind, it stops trying other kinds.

Example:

- If it finds any `AGENTS.md`, it will load all matching `AGENTS.md` discovered in the upward scan,
  and will not consider `CLAUDE.md` or `CONTEXT.md`.

## Rule Files (Global)

Global rule files are also supported. Typical locations:

- `~/.config/opencode/AGENTS.md`
- `~/.claude/CLAUDE.md` (can be disabled by env)
- `${OPENCODE_CONFIG_DIR}/AGENTS.md` (if set)

## Config-Driven `instructions[]`

In `opencode.json` you can specify additional instruction sources.

Supported forms:

- `https://...` or `http://...` URLs (fetched with a 5s timeout; failures become empty)
- `~/...` paths (expanded)
- Absolute paths (globbed by basename in that directory)
- Relative patterns (glob-up semantics)

Example:

```json
{
  "instructions": [
    "./docs/ai/*.md",
    "~/notes/prompt-snippets.md",
    "https://example.com/my-team-rules.txt"
  ]
}
```

## OpenAgentic-Specific: `.claude` Compatibility Blocks

This repo supports optional `.claude` compatibility blocks (project memory + command list), but they are opt-in.

They are only included when `setting_sources` includes `"claude"`.

If you are using the CLI only, you generally do not need this.

## Security Notes

- URL instructions are remote prompt injection surfaces. Keep them on HTTPS, and prefer allowlisting domains.
- Rule files are arbitrary text that gets elevated into the system prompt; treat them like code.
