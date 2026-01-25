import asyncio
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_mcp_oauth_flow_authorization_code import _OAuthTestServer


class TestCliMcpOauthAuthCommand(unittest.TestCase):
    def test_cmd_mcp_auth_runs_oauth_flow_when_no_token(self) -> None:
        from openagentic_cli.mcp_cmd import cmd_mcp_auth
        from openagentic_sdk.mcp.auth_store import McpAuthStore

        srv = _OAuthTestServer()
        srv.start()
        try:
            with TemporaryDirectory() as td:
                root = Path(td)
                os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
                os.environ["RIGHTCODE_API_KEY"] = "x"
                os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
                os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
                try:
                    (root / "opencode.json").write_text(
                        '{"mcp": {"srv": {"type": "remote", "url": "' + (srv.base_url + '/mcp') + '", "oauth": {"scope": "mcp:tools"}}}}\n',
                        encoding="utf-8",
                    )

                    async def open_url(url: str) -> None:
                        import urllib.request

                        def _hit() -> None:
                            with urllib.request.urlopen(url) as _resp:  # noqa: S310
                                _resp.read(0)

                        await asyncio.to_thread(_hit)

                    out = cmd_mcp_auth(cwd=str(root), name="srv", token=None, open_url=open_url, callback_port=0)
                    self.assertIn("OAuth", out)

                    store = McpAuthStore.load_default()
                    entry = store.get_for_url("srv", server_url=srv.base_url + "/mcp")
                    self.assertIsNotNone(entry)
                    assert entry is not None
                    self.assertIsNotNone(entry.tokens)
                    assert entry.tokens is not None
                    self.assertEqual(entry.tokens.access_token, "tok1")
                finally:
                    os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                    os.environ.pop("RIGHTCODE_API_KEY", None)
                    os.environ.pop("OPENCODE_CONFIG_DIR", None)
                    os.environ.pop("OPENCODE_TEST_HOME", None)
        finally:
            srv.close()


if __name__ == "__main__":
    unittest.main()
