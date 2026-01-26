from __future__ import annotations

import asyncio
import os
from dataclasses import replace

from _common import example_artifact_dir, repo_root, rightcode_options

from openagentic_sdk import AssistantMessage, TextBlock, create_sdk_mcp_server, query_messages, tool


@tool("get_token", "Return a token string", {})
async def get_token(_args):  # noqa: ANN001
    token = os.environ.get("OPENAGENTIC_CAS_TOKEN") or "MCP_TOKEN"
    return {"content": [{"type": "text", "text": token}]}


def _print_assistant_text(msg: object) -> None:
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                text = (block.text or "").strip()
                if text:
                    print(text)


async def main() -> None:
    print("=== CAS Scenario: SDK MCP tools (in-process) ===")
    out_dir = example_artifact_dir("cas_07")
    server = create_sdk_mcp_server(name="demo-tools", version="1.0.0", tools=[get_token])

    opts0 = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
        allowed_tools=["mcp__demo__get_token"],
        permission_mode="bypass",
        interactive=False,
    )
    opts = replace(opts0, mcp_servers={"demo": server})

    prompt = (
        "Call the tool mcp__demo__get_token.\n"
        "After getting the tool result, reply with exactly the token."
    )
    async for msg in query_messages(prompt=prompt, options=opts):
        _print_assistant_text(msg)


if __name__ == "__main__":
    asyncio.run(main())

