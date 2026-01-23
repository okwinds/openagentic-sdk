from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

from open_agent_sdk import create_sdk_mcp_server, query, tool


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {
        "content": [
            {"type": "text", "text": str(float(args["a"]) + float(args["b"]))},
        ]
    }

async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[add])
        options = replace(
            rightcode_options(cwd=root, project_dir=root, allowed_tools=["mcp__calc__add"]),
            mcp_servers={"calc": server},
        )
        prompt = (
            "Call the tool mcp__calc__add with a=1 and b=2. "
            "After getting the tool result, reply with exactly: MCP_OK:<sum>."
        )
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
            elif ev.type == "result":
                print(f"[result] session_id={ev.session_id} stop_reason={ev.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
