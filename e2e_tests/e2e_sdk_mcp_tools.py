from __future__ import annotations

import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import openagentic_sdk
from openagentic_sdk import create_sdk_mcp_server, tool

from e2e_tests._harness import make_options


class TestE2ESdkMcpTools(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_tool_is_executed_and_token_returned(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            token = f"MCP_{uuid.uuid4().hex}"

            @tool("get_token", "Return a random token", {})
            async def get_token(_args):  # noqa: ANN001
                return {"content": [{"type": "text", "text": token}]}

            server = create_sdk_mcp_server(name="t", tools=[get_token])
            opts0 = make_options(root, allowed_tools=["mcp__demo__get_token"])
            opts = replace(opts0, mcp_servers={"demo": server})

            prompt = (
                "Call the tool mcp__demo__get_token.\n"
                "After getting the tool result, reply with exactly the token."
            )

            events: list[object] = []
            async for ev in openagentic_sdk.query(prompt=prompt, options=opts):
                events.append(ev)

            saw_tool = any(
                getattr(e, "type", None) == "tool.use" and getattr(e, "name", None) == "mcp__demo__get_token"
                for e in events
            )
            final_texts = [getattr(e, "final_text", "") for e in events if getattr(e, "type", None) == "result"]
            final_text = final_texts[-1] if final_texts else ""

            self.assertTrue(saw_tool)
            self.assertIn(token, final_text)


if __name__ == "__main__":
    unittest.main()

