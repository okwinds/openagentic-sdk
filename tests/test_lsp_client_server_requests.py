import asyncio
import sys
import tempfile
import unittest
from pathlib import Path


class TestLspClientServerRequests(unittest.IsolatedAsyncioTestCase):
    async def test_client_responds_to_workspace_configuration(self) -> None:
        from openagentic_sdk.lsp.client import StdioLspClient

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fixture = Path(__file__).resolve().parent / "fixtures" / "lsp_stub_server_client_requests.py"
            self.assertTrue(fixture.exists())

            c = StdioLspClient(command=[sys.executable, str(fixture)], cwd=str(root))
            try:
                # If the client doesn't respond to server->client requests, the
                # server will never reply to initialize.
                await asyncio.wait_for(c.ensure_initialized(root_path=str(root)), timeout=2.0)
            finally:
                await c.close()


if __name__ == "__main__":
    unittest.main()
