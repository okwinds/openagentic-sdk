import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class AskProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        if not any(m.get("role") == "tool" for m in messages):
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(
                        tool_use_id="call_1",
                        name="AskUserQuestion",
                        arguments={
                            "questions": [
                                {
                                    "question": "Pick one",
                                    "header": "pick",
                                    "options": [
                                        {"label": "A", "description": "opt a"},
                                        {"label": "B", "description": "opt b"},
                                    ],
                                    "multiSelect": False,
                                }
                            ]
                        },
                    )
                ],
            )
        tool_msg = next(m for m in messages if m.get("role") == "tool")
        data = json.loads(tool_msg.get("content") or "{}")
        ans = (data.get("answers") or {}).get("Pick one")
        return ModelOutput(assistant_text=f"answer={ans}", tool_calls=[])


class TestAskUserQuestionTool(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_asks_and_returns_answer(self) -> None:
        async def user_answerer(q):  # noqa: ANN001
            _ = q
            return "A"

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=AskProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass", user_answerer=user_answerer),
                session_store=store,
                allowed_tools=["AskUserQuestion"],
            )

            import openagentic_sdk

            r = await openagentic_sdk.run(prompt="hi", options=options)
            self.assertIn("answer=A", r.final_text)


if __name__ == "__main__":
    unittest.main()

