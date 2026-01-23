import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.bash import BashTool
from openagentic_sdk.tools.registry import ToolRegistry


class CaptureToolsProvider:
    name = "openai-compatible"

    def __init__(self) -> None:
        self.captured_tools = None

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, api_key)
        self.captured_tools = list(tools)
        return ModelOutput(assistant_text="ok", tool_calls=[], usage=None, raw=None)


class TestRuntimeToolSchemaContext(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_passes_cwd_into_openai_tool_descriptions(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            provider = CaptureToolsProvider()
            tools = ToolRegistry([BashTool()])
            options = OpenAgentOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                tools=tools,
                allowed_tools=["Bash"],
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            async for _ in openagentic_sdk.query(prompt="hi", options=options):
                pass

            self.assertIsNotNone(provider.captured_tools)
            bash_schema = next(t for t in provider.captured_tools if t.get("function", {}).get("name") == "Bash")
            desc = bash_schema["function"]["description"]
            self.assertIn(str(root), desc)


if __name__ == "__main__":
    unittest.main()

