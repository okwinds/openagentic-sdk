import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.client import OpenAgentSDKClient
from openagentic_sdk.messages import ResultMessage
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class SlowStreamingProvider:
    name = "slow-stream"

    async def stream(self, *, model, messages, tools=(), api_key=None):
        _ = (model, messages, tools, api_key)
        for _i in range(1000):
            yield {"type": "text_delta", "delta": "x"}
            await asyncio.sleep(0)
        yield {"type": "done"}


class TestInterrupt(unittest.IsolatedAsyncioTestCase):
    async def test_interrupt_stops_execution(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgenticOptions(
                provider=SlowStreamingProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                include_partial_messages=True,
            )

            async with OpenAgentSDKClient(options) as client:
                await client.query("hi")

                async def trigger():
                    await asyncio.sleep(0)
                    await client.interrupt()

                asyncio.create_task(trigger())

                result_msgs = [m async for m in client.receive_response() if isinstance(m, ResultMessage)]
                self.assertEqual(len(result_msgs), 1)
                self.assertTrue(result_msgs[0].is_error)
                self.assertEqual(result_msgs[0].result, "")


if __name__ == "__main__":
    unittest.main()

