from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options

from openagentic_sdk import (
    AssistantMessage,
    OpenAgentSDKClient,
    ResultMessage,
    TextBlock,
)


def _display(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(f"Assistant: {text}")
    elif isinstance(msg, ResultMessage):
        print(f"[done] session_id={msg.session_id}")


async def main() -> None:
    print("=== CAS Streaming Client: multi-turn conversation ===")
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])

    async with OpenAgentSDKClient(options=options) as client:
        print("User: Reply with exactly: CLIENT_TURN1_OK")
        await client.query("Reply with exactly: CLIENT_TURN1_OK")
        async for msg in client.receive_response():
            _display(msg)

        print("\nUser: Reply with exactly: CLIENT_TURN2_OK")
        await client.query("Reply with exactly: CLIENT_TURN2_OK")
        async for msg in client.receive_response():
            _display(msg)


if __name__ == "__main__":
    asyncio.run(main())

