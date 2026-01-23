import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput, ToolCall
from open_agent_sdk.sessions.store import FileSessionStore
from open_agent_sdk.tools.registry import ToolRegistry
from open_agent_sdk.tools.web_fetch import WebFetchTool


class WebFetchPromptProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(
                        tool_use_id="call_1",
                        name="WebFetch",
                        arguments={"url": "https://example.com", "prompt": "Summarize"},
                    )
                ],
            )
        if self.calls == 2:
            # Internal summarization call triggered by runtime.
            return ModelOutput(assistant_text="SUMMARY", tool_calls=[])

        tool_msg = next(m for m in messages if m.get("role") == "tool")
        data = json.loads(tool_msg.get("content") or "{}")
        return ModelOutput(assistant_text=f"final:{data.get('response')}", tool_calls=[])


class TestWebFetchPrompt(unittest.IsolatedAsyncioTestCase):
    async def test_web_fetch_prompt_generates_response(self) -> None:
        def transport(url, headers):
            _ = (url, headers)
            return 200, {"content-type": "text/plain"}, b"hello world"

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([WebFetchTool(transport=transport, allow_private_networks=True)])
            options = OpenAgentOptions(
                provider=WebFetchPromptProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                tools=tools,
                allowed_tools=["WebFetch"],
                permission_gate=PermissionGate(permission_mode="bypass"),
            )
            import open_agent_sdk

            r = await open_agent_sdk.run(prompt="hi", options=options)
            self.assertEqual(r.final_text, "final:SUMMARY")


if __name__ == "__main__":
    unittest.main()

