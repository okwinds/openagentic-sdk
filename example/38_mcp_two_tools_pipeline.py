from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import create_sdk_mcp_server, query, tool


@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": str(float(args["a"]) + float(args["b"]))}]}


@tool("mul", "Multiply two numbers", {"a": float, "b": float})
async def mul(args):
    return {"content": [{"type": "text", "text": str(float(args["a"]) * float(args["b"]))}]}


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        server = create_sdk_mcp_server(name="calculator", version="1.0.0", tools=[add, mul])

        options = replace(
            rightcode_options(
                cwd=root,
                project_dir=root,
                allowed_tools=["mcp__calc__add", "mcp__calc__mul"],
                permission_mode="bypass",
                interactive=False,
            ),
            mcp_servers={"calc": server},
        )
        prompt = (
            "Compute (1 + 2) * 3 using the MCP tools.\n"
            "1) Call mcp__calc__add with a=1 b=2.\n"
            "2) Take the result and call mcp__calc__mul with a=<sum> b=3.\n"
            "Finally reply with MCP_PIPELINE_OK:<result>."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())

