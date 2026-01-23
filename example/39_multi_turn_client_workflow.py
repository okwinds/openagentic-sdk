from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled

from open_agent_sdk.client import OpenAgentSDKClient


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    renderer = ConsoleRenderer(debug=console_debug_enabled())

    async with OpenAgentSDKClient(options) as client:
        await client.query("Create a 3-item TODO list for 'write a weekly status update' using TodoWrite. Then say TURN1_OK.")
        async for m in client.receive_response():
            renderer.on_message(m)

        await client.query("Update the TODOs: mark one completed via TodoWrite. Then say TURN2_OK.")
        async for m in client.receive_response():
            renderer.on_message(m)


if __name__ == "__main__":
    asyncio.run(main())
