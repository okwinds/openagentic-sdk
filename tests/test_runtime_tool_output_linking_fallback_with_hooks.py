import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.registry import ToolRegistry


class FakeRightcodeToolOutputLinkingProviderWithHooks:
    """Simulates a gateway that rejects tool outputs unless the call is present.

    This variant matches a common real-world failure mode: hooks may prepend a
    role-based system/developer message even when the runtime is trying to send
    only `function_call_output` items (Responses incremental mode).
    """

    name = "fake-rightcode-tool-linking-with-hooks"

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

        # Reject any request that includes tool outputs without the matching call,
        # even if role-based system messages are present.
        has_output = any(isinstance(i, dict) and i.get("type") == "function_call_output" for i in input)
        has_call = any(isinstance(i, dict) and i.get("type") == "function_call" for i in input)
        if has_output and not has_call:
            raise RuntimeError(
                'HTTP 400 from https://www.right.codes/codex/v1/responses: {"error":{"message":"No tool call found for function call output with call_id call_1.","type":"invalid_request_error","param":"input","code":null}}'
            )

        # Fallback path: accept combined Responses-style tool call + output items.
        if has_call and has_output:
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


class TestRuntimeToolOutputLinkingFallbackWithHooks(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_falls_back_even_when_hooks_prepend_system_messages(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")

            store = FileSessionStore(root_dir=root)
            tools = ToolRegistry([ReadTool()])
            provider = FakeRightcodeToolOutputLinkingProviderWithHooks()

            async def _prepend_system(payload):
                msgs = payload.get("messages")
                if not isinstance(msgs, list) or not msgs:
                    return HookDecision()
                # Only rewrite the tool-output-only continuation so we simulate
                # hook pipelines that always ensure a system context message.
                if all(isinstance(i, dict) and i.get("type") == "function_call_output" for i in msgs):
                    return HookDecision(
                        override_messages=[{"role": "system", "content": "hook"}, *msgs],
                        action="prepend_system",
                    )
                return HookDecision()

            hooks = HookEngine(
                before_model_call=[HookMatcher(name="prepend-system", tool_name_pattern="*", hook=_prepend_system)],
                enable_message_rewrite_hooks=True,
            )

            options = OpenAgenticOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                tools=tools,
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                hooks=hooks,
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


if __name__ == "__main__":
    unittest.main()
