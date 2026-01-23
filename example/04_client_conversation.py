from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_client_turn, console_debug_enabled

from open_agent_sdk.client import OpenAgentSDKClient


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    debug = console_debug_enabled()
    renderer = ConsoleRenderer(debug=debug)

    async with OpenAgentSDKClient(options) as client:
        r1 = await console_client_turn(client=client, prompt="Say: CLIENT_TURN_1_OK", renderer=renderer)
        if r1 is not None:
            print(f"turn1: {r1.result}")
            if debug:
                print(f"[debug] session_id={r1.session_id}")

        r2 = await console_client_turn(
            client=client,
            prompt="Say: CLIENT_TURN_2_OK (and mention you remember turn 1)",
            renderer=renderer,
        )
        if r2 is not None:
            print(f"turn2: {r2.result}")
            if debug:
                print(f"[debug] session_id={r2.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
