from __future__ import annotations

import asyncio

from _common import repo_root, rightcode_options

from open_agent_sdk import run


async def main() -> None:
    options = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    r = await run(prompt="Reply with exactly: RUN_BASIC_OK", options=options)
    print(r.final_text)


if __name__ == "__main__":
    asyncio.run(main())
