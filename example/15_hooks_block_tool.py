from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query
from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher


async def _block_bash(_payload):
    return HookDecision(block=True, block_reason="No bash in this example", action="block")


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        hooks = HookEngine(pre_tool_use=[HookMatcher(name="block-bash", tool_name_pattern="Bash", hook=_block_bash)])
        options = replace(rightcode_options(cwd=root, project_dir=root, allowed_tools=["Bash"]), hooks=hooks)
        prompt = "Use the Bash tool to run: echo blocked-by-hook. Then reply with HOOK_BLOCK_OK."
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
