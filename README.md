# Open Agent SDK (Python)

Pure-Python, open-source Agent SDK inspired by the Claude Agent SDK programming model.

Status: early scaffold (no published API stability yet).

## Quickstart (local)

Run unit tests:

`PYTHONPATH=packages/sdk/open-agent-sdk python3 -m unittest discover -s packages/sdk/open-agent-sdk/tests -p 'test_*.py' -q`

## Usage

Streaming:

```py
import asyncio
from open_agent_sdk import OpenAgentOptions, query
from open_agent_sdk.providers import OpenAIProvider
from open_agent_sdk.permissions import PermissionGate


async def main() -> None:
    options = OpenAgentOptions(
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
from open_agent_sdk import OpenAgentOptions, run
from open_agent_sdk.providers import OpenAIProvider
from open_agent_sdk.permissions import PermissionGate


async def main() -> None:
    options = OpenAgentOptions(
        provider=OpenAIProvider(),
        model="gpt-4.1-mini",
        api_key="...",
        permission_gate=PermissionGate(permission_mode="callback", approver=lambda *_: True),
    )
    result = await run(prompt="Explain this project", options=options)
    print(result.final_text)


asyncio.run(main())
```

## Built-in tools

Default registry includes:

- `Read`, `Write`, `Edit`
- `Glob`, `Grep`
- `Bash`
- `WebFetch`
- `WebSearch` (Tavily; requires `TAVILY_API_KEY`)
- `SlashCommand` (loads `.claude/commands/<name>.md`)
- `SkillList`, `SkillLoad`, `SkillActivate` (for `.claude/skills/**/SKILL.md`)

## `.claude` compatibility

When `setting_sources=["project"]`, the SDK can index:

- `CLAUDE.md` or `.claude/CLAUDE.md` (memory)
- `.claude/skills/**/SKILL.md`
- `.claude/commands/*.md`

When `setting_sources=["project"]`, `query()` prepends a `system` message with project memory + skills/commands index; `SkillActivate` adds an "Active Skills" section persisted via `skill.activated` events (survives `resume`).

## MCP (placeholder)

MCP is not implemented yet, but the API is expected to reserve fields like `mcp_servers` in options.

## Event compatibility

- `events.jsonl` is forward-compatible for added fields: deserialization ignores unknown keys on known event `type`s.
- Unknown event `type`s raise `open_agent_sdk.errors.UnknownEventTypeError`.
