from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, OpenAgentSDKClient, ResultMessage, TextBlock


def _display(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = block.text or ""
                if text:
                    print(text, end="", flush=True)
    elif isinstance(msg, ResultMessage):
        print(f"\n[done] subtype={msg.subtype} session_id={msg.session_id}")


async def main() -> None:
    print("=== CAS Streaming Client: interrupt ===")
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])

    async with OpenAgentSDKClient(options=options) as client:
        print("User: Start a long response (we will interrupt)...")
        await client.query(
            "Write a long list of 200 items, one per line, with a small explanation per item."
        )

        async def consume() -> None:
            async for msg in client.receive_response():
                _display(msg)

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.5)
        print("\n\n[interrupting...]\n")
        await client.interrupt()
        await task

        print("\nUser: Reply with exactly: INTERRUPT_FOLLOWUP_OK")
        await client.query("Reply with exactly: INTERRUPT_FOLLOWUP_OK")
        async for msg in client.receive_response():
            _display(msg)


if __name__ == "__main__":
    asyncio.run(main())

