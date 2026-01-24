import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.api import run
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class CapturingProvider:
    name = "fake"

    def __init__(self) -> None:
        self.seen_messages = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        self.seen_messages = list(messages)
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestPromptStreamingInput(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_prompt_is_concatenated(self) -> None:
        async def message_stream():
            yield {"type": "text", "text": "Analyze:"}
            await asyncio.sleep(0)
            yield {"type": "text", "text": "A"}
            yield {"type": "text", "text": "B"}

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            provider = CapturingProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
            )
            result = await run(prompt=message_stream(), options=options)
            self.assertEqual(result.final_text, "ok")
            self.assertEqual(provider.seen_messages[-1]["role"], "user")
            self.assertEqual(provider.seen_messages[-1]["content"], "Analyze:\nA\nB")


if __name__ == "__main__":
    unittest.main()

