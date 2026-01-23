import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class ProviderAsksTool:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        return ModelOutput(assistant_text=None, tool_calls=[ToolCall("tc1", "Bash", {"command": "echo hi"})])


class TestAskUserQuestion(unittest.IsolatedAsyncioTestCase):
    async def test_emits_question_and_uses_answerer(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)

            async def answerer(_q):
                return "yes"

            options = OpenAgentOptions(
                provider=ProviderAsksTool(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(
                    permission_mode="prompt",
                    interactive=False,
                    user_answerer=answerer,
                ),
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="go", options=options):
                events.append(e)
                if getattr(e, "type", None) == "tool.result":
                    break
            self.assertTrue(any(getattr(e, "type", None) == "user.question" for e in events))


if __name__ == "__main__":
    unittest.main()

