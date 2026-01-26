from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, StreamEvent, TextBlock, query_messages


async def _run(*, include_partial: bool) -> None:
    opts0 = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    opts = replace(opts0, include_partial_messages=include_partial, max_steps=10)

    saw_delta = False
    async for msg in query_messages(
        prompt="Write a short two-sentence answer about what an async iterator is.",
        options=opts,
    ):
        if isinstance(msg, StreamEvent) and msg.event.get("type") == "text_delta":
            saw_delta = True
            print(str(msg), end="", flush=True)
            continue
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    text = block.text or ""
                    if text:
                        print(text, end="", flush=True)

    print()
    print(f"[include_partial_messages={include_partial}] saw_text_delta={saw_delta}")


async def main() -> None:
    print("=== CAS Scenario: include_partial_messages ===")
    print("\n--- partial messages disabled ---")
    await _run(include_partial=False)
    print("\n--- partial messages enabled ---")
    await _run(include_partial=True)


if __name__ == "__main__":
    asyncio.run(main())

