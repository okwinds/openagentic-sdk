from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query
from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher


async def _rewrite_read(payload):
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, dict) and tool_input.get("file_path") == "a.txt":
        return HookDecision(override_tool_input={"file_path": "b.txt"}, action="rewrite_file_path")
    return HookDecision()


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.txt").write_text("AAA", encoding="utf-8")
        (root / "b.txt").write_text("BBB", encoding="utf-8")

        hooks = HookEngine(
            pre_tool_use=[
                HookMatcher(name="rewrite-read", tool_name_pattern="Read", hook=_rewrite_read),
            ]
        )
        options = replace(rightcode_options(cwd=root, project_dir=root, allowed_tools=["Read"]), hooks=hooks)

        prompt = "Use the Read tool to read file 'a.txt'. Then reply with HOOK_REWRITE_OK:<file contents>."
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
