from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from _common import example_artifact_dir, repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, TextBlock, query_messages
from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher


def _print_assistant_text(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(text)


async def main() -> None:
    print("=== CAS Scenario: hooks (rewrite tool input) ===")
    out_dir = example_artifact_dir("cas_05")
    token_a = os.environ.get("OPENAGENTIC_CAS_TOKEN_A") or "TOKEN_A"
    token_b = os.environ.get("OPENAGENTIC_CAS_TOKEN_B") or "TOKEN_B"

    a_path = Path(out_dir) / "a.txt"
    b_path = Path(out_dir) / "b.txt"
    a_path.write_text(token_a, encoding="utf-8")
    b_path.write_text(token_b, encoding="utf-8")

    async def rewrite_read(payload: Mapping[str, Any]) -> HookDecision:
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return HookDecision()
        fp = tool_input.get("file_path", tool_input.get("filePath"))
        if not isinstance(fp, str) or not fp.endswith("a.txt"):
            return HookDecision()
        updated = dict(tool_input)
        updated["file_path"] = "./b.txt"
        return HookDecision(override_tool_input=updated, action="rewrite_read_to_b")

    hooks = HookEngine(
        pre_tool_use=[
            HookMatcher(
                name="rewrite-read-a-to-b",
                tool_name_pattern="Read",
                hook=rewrite_read,
            )
        ]
    )

    opts0 = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
        allowed_tools=["Read"],
        permission_mode="bypass",
        interactive=False,
    )
    opts = replace(opts0, hooks=hooks, max_steps=20)

    prompt = (
        "Use the Read tool to read a.txt and reply with exactly the file content.\n"
        "Do not guess."
    )
    async for msg in query_messages(prompt=prompt, options=opts):
        _print_assistant_text(msg)

    print("\nExpected: output should match b.txt (because hook rewrote the Read input).")
    print(f"a.txt={a_path} b.txt={b_path}")


if __name__ == "__main__":
    asyncio.run(main())

