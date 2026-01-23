import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.messages import ResultMessage
from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput
from open_agent_sdk.sessions.store import FileSessionStore


class FakeProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestSDKClient(unittest.IsolatedAsyncioTestCase):
    async def test_client_reuses_session_id(self) -> None:
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

            async with OpenAgentSDKClient(options) as client:
                await client.query("hi")
                r1 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]

                await client.query("follow up")
                r2 = [m async for m in client.receive_response() if isinstance(m, ResultMessage)][0]

            self.assertEqual(r1.session_id, r2.session_id)


if __name__ == "__main__":
    unittest.main()

