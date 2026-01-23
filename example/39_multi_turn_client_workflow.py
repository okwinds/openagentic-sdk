from __future__ import annotations

import asyncio

from _common import example_debug_enabled, repo_root, rightcode_options

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.messages import ResultMessage


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    debug = example_debug_enabled()

    async with OpenAgentSDKClient(options) as client:
        await client.query("Create a 3-item TODO list for 'write a weekly status update' using TodoWrite. Then say TURN1_OK.")
        r1 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]
        print(r1.result or "")
        if debug:
            print(f"[debug] session_id={r1.session_id}")

        await client.query("Update the TODOs: mark one completed via TodoWrite. Then say TURN2_OK.")
        r2 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]
        print(r2.result or "")
        if debug:
            print(f"[debug] session_id={r2.session_id}")


if __name__ == "__main__":
    asyncio.run(main())

