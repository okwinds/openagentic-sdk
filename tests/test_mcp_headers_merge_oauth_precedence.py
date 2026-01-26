import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestMcpHeadersMergeOauthPrecedence(unittest.TestCase):
    def test_oauth_access_token_takes_precedence_over_bearer_token(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["RIGHTCODE_API_KEY"] = "x"
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root / "oa-home")
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                # Config with a remote MCP server.
                (root / "opencode.json").write_text(
                    '{"mcp": {"srv": {"type": "remote", "url": "https://example/mcp", "headers": {}}}}\n',
                    encoding="utf-8",
                )

                # Write bearer token (legacy store).
                cred_path = root / "oa-home" / "mcp" / "credentials.json"
                cred_path.parent.mkdir(parents=True, exist_ok=True)
                cred_path.write_text('{"srv": {"bearer_token": "legacy"}}\n', encoding="utf-8")

                # Write OAuth token (OpenCode-like store).
                auth_path = root / "oa-home" / "mcp" / "mcp-auth.json"
                auth_path.parent.mkdir(parents=True, exist_ok=True)
                auth_path.write_text(
                    '{"srv": {"serverUrl": "https://example/mcp", "tokens": {"accessToken": "oauth"}}}\n',
                    encoding="utf-8",
                )

                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="deny")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)

            mcp = opts.mcp_servers or {}
            srv = mcp.get("srv") if isinstance(mcp, dict) else None
            self.assertIsInstance(srv, dict)
            headers = srv.get("headers") if isinstance(srv, dict) else None
            self.assertIsInstance(headers, dict)
            auth = None
            for k, v in headers.items():
                if str(k).lower() == "authorization":
                    auth = str(v)
            self.assertEqual(auth, "Bearer oauth")


if __name__ == "__main__":
    unittest.main()
