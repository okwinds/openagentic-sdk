import unittest


class TestMcpUrlValidation(unittest.TestCase):
    def test_http_client_rejects_non_http_scheme(self) -> None:
        from openagentic_sdk.mcp.http_client import HttpMcpClient

        with self.assertRaises(ValueError):
            _ = HttpMcpClient(url="file:///etc/passwd")

    def test_oauth_manager_rejects_non_http_scheme(self) -> None:
        import asyncio

        from openagentic_sdk.mcp.oauth_flow import McpOAuthManager

        async def _run() -> None:
            mgr = McpOAuthManager(callback_port=0)

            async def open_url(_u: str) -> None:
                return

            with self.assertRaises(ValueError):
                await mgr.authenticate(server_key="srv", server_url="file:///x", scope=None, open_url=open_url)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
