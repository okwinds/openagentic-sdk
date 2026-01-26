# v2-03 Commands (Slash Commands)

This guide explains how OpenCode-style commands work in this repo.

## Using Commands

In `oa chat` or `oa run`, you can invoke a command by starting your prompt with `/`:

```
/review
```

Commands can take arguments:

```
/review src/app.py "explain risks"
```

Argument parsing is OpenCode-like:

- quoted strings are preserved
- `[Image N]` is treated as a single token

## Where Commands Come From

Commands are loaded from (highest precedence last):

- Built-ins (e.g. `init`, `review`)
- Config-defined commands in `opencode.json`
- Markdown command files discovered in config directories:
  - `{command,commands}/**/*.md` under:
    - `~/.config/opencode/`
    - project `.opencode/` (up-tree)
    - `~/.opencode/`
    - `${OPENCODE_CONFIG_DIR}`

Nested paths are preserved:

- `.opencode/commands/nested/child.md` becomes `/nested/child`

## Command Template Format

A command file is Markdown with optional YAML frontmatter.

Example `commands/review.md`:

```md
---
description: Review changes with security focus
agent: oracle
model: gpt-5
subtask: true
---

Review the staged git diff.

Run:

`!git status`
`!git diff --staged`

Focus on correctness, security, and missing tests.
```

Supported frontmatter fields:

- `description`: human-readable
- `agent`: run via Task/subagent if enabled
- `model`: model override (if supported)
- `subtask`: if true, treat as subtask (see below)

## Placeholders

Templates can use OpenCode-style placeholders:

- `$1`, `$2`, ... (1-based)
- `$ARGUMENTS` for the raw argument string

Important: the highest placeholder index "swallows" remaining arguments.

Example:

Template:

```
Search for: $1
Filters: $2
```

Invocation:

```
/search error "src/** tests/**"
```

## Shell Blocks

Backticked shell blocks starting with `!` are executed and replaced with stdout:

```
`!git status`
```

Notes:

- runs are executed concurrently
- shell execution is permission-gated

## File And Agent References (`@...`)

Commands can reference files/directories using `@path`:

```
Please review @src/app.py and @src/
```

Behavior:

- existing files/dirs become attachment parts
- if a referenced path does not exist but matches an agent name, it becomes an `agent` part

## Subtask Behavior

If a command is treated as a subtask:

- the command becomes a subtask request (Task tool)
- file parts from `@...` are not forwarded; only the text prompt is sent

This matches OpenCode's "subtask drops attachments" edge behavior.
