import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.registry import ToolRegistry


class FakeRightcodeToolOutputLinkingProvider:
    """
    Simulates a gateway that *does not* link tool outputs via previous_response_id.

    It raises the same error RightCode returns when we submit only function_call_output items.
    """

    name = "fake-rightcode-tool-linking"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def stream(self, *, model, input, tools=(), api_key=None, previous_response_id=None, store=True):
        self.calls.append(
            {
                "model": model,
                "input": list(input),
                "previous_response_id": previous_response_id,
                "store": store,
            }
        )

        # Second response: if we only got outputs, reject (can't find the call_id).
        only_outputs = all(isinstance(i, dict) and i.get("type") == "function_call_output" for i in input)
        if only_outputs:
            raise RuntimeError(
                'HTTP 400 from https://www.right.codes/codex/v1/responses: {"error":{"message":"No tool call found for function call output with call_id call_1.","type":"invalid_request_error","param":"input","code":null}}'
            )

        has_function_call = any(isinstance(i, dict) and i.get("type") == "function_call" and i.get("call_id") for i in input)
        has_function_call_output = any(
            isinstance(i, dict) and i.get("type") == "function_call_output" and i.get("call_id") for i in input
        )

        # Fallback path: accept combined Responses-style tool call + output items (no previous_response_id).
        if has_function_call and has_function_call_output:
            call = next(i for i in input if isinstance(i, dict) and i.get("type") == "function_call")
            out = next(i for i in input if isinstance(i, dict) and i.get("type") == "function_call_output")
            assert call.get("call_id") == "call_1"
            assert out.get("call_id") == "call_1"
            data = json.loads(out.get("output") or "{}")
            content = data.get("content", "")
            yield {"type": "text_delta", "delta": f"OK: {content}"}
            yield {"type": "done", "response_id": "resp_2", "usage": {"total_tokens": 2}}
            return

        # First response: request a tool call.
        yield {"type": "tool_call", "tool_call": ToolCall(tool_use_id="call_1", name="Read", arguments={"file_path": "a.txt"})}
        yield {"type": "done", "response_id": "resp_1", "usage": {"total_tokens": 1}}


class TestRuntimeToolOutputLinkingFallback(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_falls_back_when_gateway_cannot_link_tool_outputs(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([ReadTool()])
            provider = FakeRightcodeToolOutputLinkingProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            final = None
            async for e in openagentic_sdk.query(prompt="read a.txt", options=options):
                if getattr(e, "type", None) == "result":
                    final = e

            self.assertIsNotNone(final)
            self.assertEqual(getattr(final, "final_text", None), "OK: hello")
            pm = getattr(final, "provider_metadata", None)
            self.assertIsInstance(pm, dict)
            self.assertEqual(pm.get("protocol"), "responses")
            self.assertEqual(pm.get("supports_previous_response_id"), False)

            # 1) initial call (no prev id), 2) failed tool-output-only call, 3) retry with combined input.
            self.assertEqual([c["previous_response_id"] for c in provider.calls], [None, "resp_1", None])


if __name__ == "__main__":
    unittest.main()
