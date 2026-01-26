from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path

from _common import example_artifact_dir, repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, TextBlock, query_messages
from openagentic_sdk.options import AgentDefinition


def _print_assistant_text(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(text)


async def main() -> None:
    print("=== CAS Scenario: Task tool (subagent) ===")
    out_dir = example_artifact_dir("cas_08")
    token = os.environ.get("OPENAGENTIC_CAS_TOKEN") or "SUBAGENT_TOKEN"
    token_path = Path(out_dir) / "token.txt"
    token_path.write_text(token, encoding="utf-8")

    opts0 = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
        allowed_tools=["Task"],
        permission_mode="bypass",
        interactive=False,
    )
    agents = {
        "reader": AgentDefinition(
            description="Reads a file and prints its content exactly",
            prompt="You are a file reader. Use tools to read files and print contents exactly.",
            tools=["Read"],
            model=None,
        )
    }
    opts = replace(opts0, agents=agents)

    prompt = (
        "Use the Task tool with agent='reader'.\n"
        "In the Task prompt, instruct the agent to read token.txt and reply with exactly the file content.\n"
        "Do not use Read directly in the parent."
    )
    async for msg in query_messages(prompt=prompt, options=opts):
        _print_assistant_text(msg)

    print(f"\nToken file: {token_path}")


if __name__ == "__main__":
    asyncio.run(main())

