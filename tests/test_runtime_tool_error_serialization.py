import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.base import Tool, ToolContext
from openagentic_sdk.tools.registry import ToolRegistry


class BoomTool(Tool):
    name = "Boom"
    description = "always errors"
    openai_schema = {
        "type": "function",
        "function": {"name": "Boom", "description": "boom", "parameters": {"type": "object", "properties": {}}},
    }

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> Any:
        _ = (tool_input, ctx)
        raise RuntimeError("boom")


class FakeResponsesProvider:
    name = "fake-responses"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        *,
        model: str,
        input,
        tools=(),
        api_key=None,
        previous_response_id=None,
        store=True,
        include=(),
        instructions=None,
    ):
        _ = (tools, api_key, store, include, instructions)
        self.calls.append({"model": model, "input": list(input), "previous_response_id": previous_response_id})
        if previous_response_id is None:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="call_1", name="Boom", arguments={})],
                usage={"total_tokens": 1},
                raw=None,
                response_id="resp_1",
            )

        tool_item = next(i for i in input if isinstance(i, dict) and i.get("type") == "function_call_output")
        payload = json.loads(tool_item.get("output") or "null")
        # Parity requirement: the model must see the error message, not `null`.
        if not (isinstance(payload, dict) and payload.get("is_error") is True and isinstance(payload.get("error_message"), str)):
            raise AssertionError(f"expected structured tool error, got: {payload!r}")

        return ModelOutput(
            assistant_text="ok",
            tool_calls=(),
            usage={"total_tokens": 2},
            raw=None,
            response_id="resp_2",
        )


class TestRuntimeToolErrorSerialization(unittest.IsolatedAsyncioTestCase):
    async def test_tool_errors_are_serialized_to_model(self) -> None:
        import openagentic_sdk

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            provider = FakeResponsesProvider()
            tools = ToolRegistry([BoomTool()])
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            async for _e in openagentic_sdk.query(prompt="hi", options=options):
                pass


if __name__ == "__main__":
    unittest.main()
