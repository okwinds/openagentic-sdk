# OpenCode Parity v2 — Commands (Templates + Parts + Execution)

## Source of Truth (OpenCode)

- Command registry: `/mnt/e/development/opencode/packages/opencode/src/command/index.ts`
- Command execution & templating: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts` (`command()` + `resolvePromptParts()`)
- Command discovery from directories: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts` (`loadCommand()`)

## OpenCode Behavior (Detailed)

### 1) Command sources

- Built-ins:
  - `init` (create/update AGENTS.md)
  - `review` (review changes)
Reference: `Command.Default` in `command/index.ts`

Additional command sources (full parity):

- Markdown command files discovered from config directories:
  - Glob: `{command,commands}/**/*.md`
  - Directories scanned include:
    - `${XDG_CONFIG_HOME}/opencode` (Global.Path.config)
    - project `.opencode` dirs up-tree (when project discovery enabled)
    - `~/.opencode` (always)
    - `${OPENCODE_CONFIG_DIR}` (if set)
  - Names preserve nested paths (e.g. `nested/child.md` => `/nested/child`).

References:

- Directory scanning: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Name derivation: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`

- MCP prompts exposed as commands:
  - `MCP.prompts()` contributes named commands
  - Prompt arguments are mapped to `$1`, `$2`, ... in the fetched template.

Reference: `/mnt/e/development/opencode/packages/opencode/src/command/index.ts`

- Config-defined commands: `cfg.command` entries become commands.

- MCP prompts as commands:
  - `MCP.prompts()` contributes named commands
  - prompt arguments are substituted as `$1`, `$2`, ...

### 2) Argument parsing

In `session/prompt.ts`:

- Arguments are tokenized with regex that supports:
  - `[Image N]` as a single token
  - quoted strings
  - non-space sequences
- Quotes are stripped.

Reference: `argsRegex`, `quoteTrimRegex`.

Invocation path (TUI -> server):

- A server command is triggered when the prompt starts with `/` and the first token matches a known command.
- Multi-line args are preserved (remaining lines are appended with `\n`).

Reference: `/mnt/e/development/opencode/packages/opencode/src/cli/cmd/tui/component/prompt/index.tsx`

### 3) Placeholder expansion

- `$N` placeholders (1-based).
- Find the maximum placeholder index; the final placeholder "swallows" remaining args.
- `$ARGUMENTS` replaced with the full raw argument string.
- If the template uses no placeholders and user provided arguments, append arguments to the template.

Reference: `placeholderRegex` + logic in `command()`.

Important detail (must match):

- The highest-numbered placeholder index is treated as "final" and swallows all remaining arguments (joined by spaces).

### 4) Shell expansion

- Shell blocks are detected as `!` in backticks: `!`cmd``.
- Commands are executed and replaced with stdout.
- Errors are converted into a text error string.

Reference: `bashRegex` and `ConfigMarkdown.shell(template)`.

Execution details (must match):

- Shell runs are executed concurrently.
- Substitution uses stdout text (stderr not included in `.text()` output).
- Non-zero exit codes generally do not throw due to `.nothrow()`.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts`

### 5) File / agent references (`@...`)

OpenCode parses `@file` references and converts them into prompt parts:

- If `@name` points to an existing filesystem path:
  - directory becomes a file part with mime `application/x-directory`
  - file becomes a file part with mime `text/plain`
- If the path does not exist but matches an agent name, it becomes an `agent` part.

Reference: `resolvePromptParts()`.

Regex details (must match):

- `@file` parsing avoids emails and backticked `@...` and strips trailing punctuation.

Reference: `/mnt/e/development/opencode/packages/opencode/src/config/markdown.ts` and tests in `/mnt/e/development/opencode/packages/opencode/test/config/markdown.test.ts`.

Security-critical behavior (must match, but we should harden):

- `@/absolute/path` and `@~/...` are allowed and resolved to absolute filesystem paths.
- When file parts are expanded into prompt text, OpenCode bypasses the external-directory guard (`bypassCwdCheck: true`).

References:

- Part resolution: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts` (`resolvePromptParts`)
- Read tool bypass: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts` (file-part processing)
- Guard bypass check: `/mnt/e/development/opencode/packages/opencode/src/tool/read.ts` and `/mnt/e/development/opencode/packages/opencode/src/tool/external-directory.ts`

Important: this is an *attachment* model (file URL parts), not inline file contents.

### 6) Subtask behavior

If agent is a subagent and `command.subtask` is not false (or explicitly true):

- Command becomes a `subtask` part (executed via task tool), rather than normal user text.

Reference: `isSubtask` logic.

Important edge (must match):

- When a command runs as a subtask, file parts from `@...` are not forwarded; only the text prompt is used.

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/prompt.ts`

## Current State (openagentic-sdk)

- Command lookup: `openagentic_sdk/commands.py`
  - config + directory-pack commands (from `openagentic_sdk/opencode_config.py` scan)
  - `.opencode/commands/<name>.md` + `.claude/commands/<name>.md` fallback
  - global `~/.config/opencode/commands/<name>.md`
  - built-ins `init`/`review`
- Command metadata from markdown frontmatter is preserved when loaded via directory packs:
  - `description`, `agent`, `model`, `subtask` are carried through config -> `CommandTemplate`.
  - `openagentic_sdk/opencode_config.py` + `openagentic_sdk/commands.py`

- Expansion is implemented inside `openagentic_sdk/runtime.py`:
  - args tokenization matches OpenCode (`[Image N]`, quoted strings)
  - `$N` swallow semantics (max placeholder index swallows remainder)
  - `$ARGUMENTS` uses raw args string
  - shell: `!`cmd`` executed concurrently via `Bash` tool (permission-gated)
  - `@...` parsing uses OpenCode regex (shared via `openagentic_sdk/opencode_markdown.py`)
  - parity output: SlashCommand tool results include structured parts:
    - `type: text`
    - `type: file` with `url=file://...`, `mime=text/plain|application/x-directory`
    - `type: agent` with OpenCode-style "call Task tool with subagent" instruction
    - `type: subtask` drops file parts and forwards prompt text only

Evidence (tests in this repo):

- Regex parity: `tests/test_opencode_markdown_file_regex.py`
- SlashCommand templating + tool execution: `tests/test_slash_command_templating.py`
- Parts parity (agent/subtask): `tests/test_slash_command_parts_parity.py`

Remaining gaps vs OpenCode:

- User-invoked `/command ...` parsing in the CLI/TUI surface (OpenCode triggers commands when prompt starts with `/`).
- MCP prompts surfaced as commands.
- Full message-v2 part pipeline parity (OpenCode stores parts and later converts them into model messages; this repo currently keeps parts on SlashCommand tool output only).

## Plan (No-Compromise Implementation)

- Implement a command registry that matches OpenCode:
  - built-in commands with same templates
  - config-defined commands with metadata
  - directory-scanned markdown commands with metadata
  - MCP prompts surfaced as commands

- Implement OpenCode-equivalent templating:
  - exact `$N` swallow semantics
  - `$ARGUMENTS`
  - shell: `!`cmd``
  - file refs -> attachment parts (not inline)
  - agent refs -> agent parts

- Implement OpenCode command discovery (markdown frontmatter) and precedence:
  - scan `{command,commands}/**/*.md` in config directories
  - nested command names preserved
  - allow command overrides exactly as OpenCode does

- Preserve/extend our safety model:
  - shell execution must always be permission-gated
  - file attachments must respect allowlists and size caps

## TDD

- Unit tests for tokenization and placeholder behavior.
- Tests for `@file` and `@agent` conversions.
- Tests for shell blocks parsing and permission gating.
- Contract tests for command discovery precedence.

Add missing parity tests that OpenCode itself lacks:

- Ensure shell output cannot unexpectedly introduce `@...` references that cause unintended file inclusion (or explicitly accept and document it).
