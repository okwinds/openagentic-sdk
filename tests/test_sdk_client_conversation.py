import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.client import OpenAgentSDKClient
from openagentic_sdk.messages import ResultMessage
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


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
            options = OpenAgenticOptions(
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

