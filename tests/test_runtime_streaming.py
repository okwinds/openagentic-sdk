import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class FakeStreamingProvider:
    name = "fake-stream"

    async def stream(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        yield {"type": "text_delta", "delta": "he"}
        yield {"type": "text_delta", "delta": "llo"}
        yield {"type": "done"}


class TestRuntimeStreaming(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_emits_assistant_delta(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=FakeStreamingProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )
            import openagentic_sdk

            types = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                types.append(getattr(e, "type", None))
            self.assertIn("assistant.delta", types)
            self.assertIn("assistant.message", types)
            self.assertIn("result", types)


if __name__ == "__main__":
    unittest.main()

