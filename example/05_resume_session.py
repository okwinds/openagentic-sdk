from __future__ import annotations

import asyncio
from dataclasses import replace

from _common import repo_root, rightcode_options
from openagentic_sdk.console import console_debug_enabled, console_run


async def main() -> None:
    options1 = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    r1 = await console_run(prompt="Say: RESUME_TURN_1_OK", options=options1)
    debug = console_debug_enabled()
    print(f"turn1: {r1.final_text}")
    print(f"session_id={r1.session_id}")

    options2 = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    options2 = replace(options2, resume=r1.session_id)
    r2 = await console_run(prompt="Say: RESUME_TURN_2_OK (confirm you have prior context)", options=options2)
    print(f"turn2: {r2.final_text}")
    if debug:
        print(f"[debug] session_id={r2.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
