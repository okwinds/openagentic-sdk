import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput
from open_agent_sdk.sessions.store import FileSessionStore


class ExplodingProvider:
    name = "fake"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        raise RuntimeError("boom")


class TestClientExitDoesNotMask(unittest.IsolatedAsyncioTestCase):
    async def test_async_with_preserves_body_exception(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=ExplodingProvider(),
                model="fake",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
            )

            with self.assertRaises(RuntimeError) as ctx:
                async with OpenAgentSDKClient(options) as client:
                    await client.query("hi")
                    async for _ in client.receive_response():
                        pass

            self.assertIn("boom", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

