# OpenAgentic SDK (Python)

Pure-Python, open-source Agent SDK inspired by the Claude Agent SDK programming model.

Status: early (APIs may change), but the core runtime + tool loop are usable today.

This project exists for people who want the “agent runtime” experience (multi-turn sessions, tool calls, approvals,
skills/commands from `.claude/`, resumable logs) in a small, hackable Python codebase.

See `README.zh_cn.md` for a Chinese overview.

## What you get

- **A minimal agent runtime**: `run()` / streaming `query()` / CAS-style `query_messages()`.
- **A persistent session model**: durable `session_id`, `events.jsonl`, `resume=<session_id>`.
- **A real tool loop**: model requests tools → permission gate → tool execution → tool results → model continues.
- **Human-friendly console output** by default (debug mode available).
- **`.claude` compatibility**: project memory, slash commands, and skills on disk.
- **OpenAI + OpenAI-compatible providers** (the examples use a real OpenAI-compatible backend by default).

## Quickstart (local)

Prereqs: Python 3.11+.

Install (optional, for editable dev):

`pip install -e .`

Set env (examples + CLI default to RIGHTCODE):

- `RIGHTCODE_API_KEY` (required)
- `RIGHTCODE_BASE_URL` (optional, default `https://www.right.codes/codex/v1`)
- `RIGHTCODE_MODEL` (optional, default `gpt-5.2`)

Run unit tests:

`python3 -m unittest -q`

Run examples:

- `python3 example/01_run_basic.py`
- See `example/README.md` for the full list and required env vars.

## `oa` CLI

Install (editable):

`pip install -e .`

If `oa` isn't found after installation on Windows, add the scripts directory printed by pip to `PATH` (or run `python -m openagentic_cli chat`).

Optional (recommended): install ripgrep (`rg`) so the agent can search your repo quickly when using shell tools.

- Windows (PowerShell): `winget install BurntSushi.ripgrep.MSVC`
- WSL/Ubuntu: `sudo apt-get update && sudo apt-get install -y ripgrep`

Commands:

- `oa chat` (multi-turn REPL; `/help` for slash commands)
- `oa run "prompt"` (`--json`, `--no-stream`)
- `oa resume <session_id>` (alias of `oa chat --resume <session_id>`)
- `oa logs <session_id>` (summarize `events.jsonl`)

Sessions are stored under `~/.openagentic-sdk` by default (override with `OPENAGENTIC_SDK_HOME`).

## Publishing

See `docs/publishing.md`.

## Usage

Streaming:

```py
import asyncio
from openagentic_sdk import OpenAgenticOptions, query
from openagentic_sdk.providers import OpenAIProvider
from openagentic_sdk.permissions import PermissionGate


async def main() -> None:
    options = OpenAgenticOptions(
        provider=OpenAIProvider(),
        model="gpt-4.1-mini",
        api_key="...",  # OpenAI API key
        permission_gate=PermissionGate(permission_mode="prompt", interactive=True),
        setting_sources=["project"],
    )

    async for event in query(prompt="Find TODOs in this repo", options=options):
        print(event.type)


asyncio.run(main())
```

One-shot:

```py
import asyncio
from openagentic_sdk import OpenAgenticOptions, run
from openagentic_sdk.providers import OpenAIProvider
from openagentic_sdk.permissions import PermissionGate


async def main() -> None:
    options = OpenAgenticOptions(
        provider=OpenAIProvider(),
        model="gpt-4.1-mini",
        api_key="...",
        permission_gate=PermissionGate(permission_mode="callback", approver=lambda *_: True),
    )
    result = await run(prompt="Explain this project", options=options)
    print(result.final_text)


asyncio.run(main())
```

OpenAI-compatible backend (the examples default to RIGHTCODE):

```py
from openagentic_sdk import OpenAgenticOptions, run
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
from openagentic_sdk.permissions import PermissionGate

options = OpenAgenticOptions(
    provider=OpenAICompatibleProvider(base_url="https://www.right.codes/codex/v1"),
    model="gpt-5.2",
    api_key="...",  # RIGHTCODE_API_KEY
    cwd=".",
    permission_gate=PermissionGate(permission_mode="prompt", interactive=True),
    setting_sources=["project"],
)
```

## Built-in tools

Default registry includes:

- `Read`, `Write`, `Edit`
- `Glob`, `Grep`
- `Bash`
- `WebFetch`
- `WebSearch` (Tavily; requires `TAVILY_API_KEY`)
- `TodoWrite`
- `SlashCommand` (loads `.claude/commands/<name>.md`)
- `Skill` (CAS-style single tool for `.claude/skills/**/SKILL.md`)
- `SkillList`, `SkillLoad`, `SkillActivate` (legacy/compat)

For OpenAI-compatible providers, tool schemas include long-form “how to use this tool” descriptions (opencode-style)
to make the model follow rules more reliably.

## `.claude` compatibility

When `setting_sources=["project"]`, the SDK can index:

- `CLAUDE.md` or `.claude/CLAUDE.md` (memory)
- `.claude/skills/**/SKILL.md`
- `.claude/commands/*.md`

When `setting_sources=["project"]`, `query()` prepends a `system` message with project memory + skills/commands index; `SkillActivate` adds an "Active Skills" section persisted via `skill.activated` events (survives `resume`).

## Console output (human-first)

Examples use `openagentic_sdk.console.ConsoleRenderer`, which:

- Prints assistant text by default (human-friendly).
- In debug mode (`--debug` or `OPENAGENTIC_SDK_CONSOLE_DEBUG=1`), prints tool/hook/result summaries.

Try the interactive CLI chat example:

- `python3 example/45_cli_chat.py`

## Event compatibility

- `events.jsonl` is forward-compatible for added fields: deserialization ignores unknown keys on known event `type`s.
- Unknown event `type`s raise `openagentic_sdk.errors.UnknownEventTypeError`.
