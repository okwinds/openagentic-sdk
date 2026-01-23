from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import repo_root, rightcode_options

from open_agent_sdk import query_messages
from open_agent_sdk.messages import ResultMessage, StreamEvent


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    options = replace(options, include_partial_messages=True)

    async for m in query_messages(prompt="Write a short sentence. Include token QUERY_MESSAGES_OK.", options=options):
        if isinstance(m, StreamEvent):
            print(m.event.get("delta", ""), end="", flush=True)
        elif isinstance(m, ResultMessage):
            print()
            print(f"[result] subtype={m.subtype} session_id={m.session_id} result={m.result!r}")


if __name__ == "__main__":
    asyncio.run(main())
