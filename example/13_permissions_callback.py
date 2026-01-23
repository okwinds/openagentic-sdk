from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

from open_agent_sdk import query


async def _approver(tool_name, tool_input, context) -> bool:
    _ = (tool_input, context)
    return tool_name != "Bash"


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["Bash"],
            permission_mode="callback",
            interactive=False,
            approver=_approver,
        )
        prompt = "Use the Bash tool to run: echo should-be-denied. Then reply with CALLBACK_OK."
        async for ev in query(prompt=prompt, options=options):
            if ev.type in ("tool.use", "tool.result", "result"):
                print(f"[{ev.type}] {ev}")


if __name__ == "__main__":
    asyncio.run(main())
