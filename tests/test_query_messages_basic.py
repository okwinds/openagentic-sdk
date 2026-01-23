import unittest

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput
from open_agent_sdk.sessions.store import FileSessionStore
from open_agent_sdk.message_query import query_messages


class FakeProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestQueryMessages(unittest.IsolatedAsyncioTestCase):
    async def test_query_messages_yields_result_message(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from open_agent_sdk.messages import ResultMessage

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=FakeProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
            )
            out = []
            async for m in query_messages(prompt="hi", options=options):
                out.append(m)
            self.assertTrue(any(isinstance(x, ResultMessage) for x in out))


if __name__ == "__main__":
    unittest.main()

