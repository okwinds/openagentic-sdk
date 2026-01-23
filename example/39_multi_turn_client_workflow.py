from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_client_turn, console_debug_enabled

from openagentic_sdk.client import OpenAgentSDKClient


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
        await console_client_turn(
            client=client,
            prompt="Create a 3-item TODO list for 'write a weekly status update' using TodoWrite. Then say TURN1_OK.",
            renderer=renderer,
        )

        await console_client_turn(
            client=client,
            prompt="Update the TODOs: mark one completed via TodoWrite. Then say TURN2_OK.",
            renderer=renderer,
        )


if __name__ == "__main__":
    asyncio.run(main())
