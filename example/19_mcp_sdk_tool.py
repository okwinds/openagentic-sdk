from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query

from openagentic_sdk import create_sdk_mcp_server, tool


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
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
