import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.seen_inputs = []
        self.seen_previous_ids = []
        self.calls = 0

    async def complete(self, *, model, input, tools=(), api_key=None, previous_response_id=None, store=True):
        _ = (model, tools, api_key, store)
        self.seen_inputs.append(list(input))
        self.seen_previous_ids.append(previous_response_id)
        self.calls += 1
        if self.calls == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall("tc1", "Read", {"file_path": "a.txt"})],
                response_id="resp_1",
            )
        return ModelOutput(assistant_text="done", tool_calls=[], response_id="resp_2")


class TestResumeRebuild(unittest.IsolatedAsyncioTestCase):
    async def test_resume_uses_previous_response_id(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            store = FileSessionStore(root_dir=root)

            provider1 = FakeProvider()
            options1 = OpenAgenticOptions(
                provider=provider1,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )

            import openagentic_sdk

            events1 = []
            async for e in openagentic_sdk.query(prompt="read it", options=options1):
                events1.append(e)
            sid = next(e.session_id for e in events1 if getattr(e, "type", None) == "system.init")

            provider2 = FakeProvider()
            options2 = OpenAgenticOptions(
                provider=provider2,
                model="fake",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                resume=sid,
            )

            async for _ in openagentic_sdk.query(prompt="continue", options=options2):
                pass

            # The resumed run should chain from the previous response id instead of reconstructing full history.
            self.assertGreaterEqual(len(provider2.seen_previous_ids), 1)
            self.assertEqual(provider2.seen_previous_ids[0], "resp_2")


if __name__ == "__main__":
    unittest.main()
