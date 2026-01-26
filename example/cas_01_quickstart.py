from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path

from _common import (
    example_artifact_dir,
    example_offline_enabled,
    repo_root,
    rightcode_options,
)

from openagentic_sdk import AssistantMessage, TextBlock, query_messages


def _print_assistant_text(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(text)


async def basic_query() -> None:
    print("=== CAS Quickstart: basic query ===")
    opts = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    async for msg in query_messages(prompt="Reply with exactly: CAS_QUICKSTART_BASIC_OK", options=opts):
        _print_assistant_text(msg)
    print()


async def with_options() -> None:
    print("=== CAS Quickstart: with options (system_prompt) ===")
    opts0 = rightcode_options(cwd=repo_root(), project_dir=repo_root(), allowed_tools=[])
    opts = replace(
        opts0,
        system_prompt="You are a helpful assistant that answers in exactly one short sentence.",
        max_steps=10,
    )
    async for msg in query_messages(prompt="Explain what Python is.", options=opts):
        _print_assistant_text(msg)
    print()


async def with_tools() -> None:
    print("=== CAS Quickstart: with tools (Write + Read) ===")
    out_dir = example_artifact_dir("cas_01")
    token = os.environ.get("OPENAGENTIC_CAS_TOKEN") or "HELLO_WORLD_TOKEN"
    target = Path(out_dir) / "hello.txt"

    async def allow_all(tool_name: str, tool_input: dict, context: dict) -> bool:  # noqa: ARG001
        return True

    opts = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
        allowed_tools=["Write", "Read"],
        permission_mode="callback",
        interactive=False,
        approver=allow_all,
    )

    prompt = (
        "Create a file named hello.txt with exactly this content (no extra whitespace):\n"
        f"{token}\n\n"
        "Then read hello.txt and reply with exactly the file content."
    )
    async for msg in query_messages(prompt=prompt, options=opts):
        _print_assistant_text(msg)

    if not example_offline_enabled():
        if target.exists():
            print(f"\nWrote: {target}")
        else:
            print(f"\nNote: expected file not found: {target}")
    print()


async def main() -> None:
    await basic_query()
    await with_options()
    await with_tools()


if __name__ == "__main__":
    asyncio.run(main())

