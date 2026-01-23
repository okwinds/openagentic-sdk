from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])

    async for ev in query(prompt="Write a short sentence about streaming. Include token STREAM_OK.", options=options):
        if ev.type == "assistant.delta":
            print(ev.text_delta, end="", flush=True)
        elif ev.type == "assistant.message":
            print()
            print(f"[assistant.message] {ev.text}")
        elif ev.type == "result":
            print(f"[result] stop_reason={ev.stop_reason} session_id={ev.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
