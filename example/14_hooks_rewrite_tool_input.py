from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

from open_agent_sdk import query
from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher


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
        async for ev in query(prompt=prompt, options=options):
            if ev.type == "assistant.delta":
                print(ev.text_delta, end="", flush=True)
            elif ev.type == "assistant.message":
                print()
                print(ev.text)
            elif ev.type == "tool.use":
                print(f"\n[tool.use] {ev.name} {ev.input}")
            elif ev.type == "tool.result":
                print(f"[tool.result] error={ev.is_error} output={ev.output}")
            elif ev.type == "hook.event":
                print(f"[hook.event] {ev.name} action={ev.action} matched={ev.matched}")
            elif ev.type == "result":
                print(f"[result] session_id={ev.session_id} stop_reason={ev.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
