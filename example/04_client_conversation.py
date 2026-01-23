from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.messages import ResultMessage


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])

    async with OpenAgentSDKClient(options) as client:
        await client.query("Say: CLIENT_TURN_1_OK")
        r1 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]
        print(f"turn1 session_id={r1.session_id} result={r1.result!r}")

        await client.query("Say: CLIENT_TURN_2_OK (and mention you remember turn 1)")
        r2 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]
        print(f"turn2 session_id={r2.session_id} result={r2.result!r}")


if __name__ == "__main__":
    asyncio.run(main())
