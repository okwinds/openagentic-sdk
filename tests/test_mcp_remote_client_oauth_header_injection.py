import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestRemoteMcpClientOauthHeaderInjection(unittest.TestCase):
    def test_injects_oauth_token_when_available(self) -> None:
        from openagentic_sdk.mcp.remote_client import RemoteMcpClient

        with TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENAGENTIC_SDK_HOME"] = str(root)
            try:
                # Seed OpenCode-like auth store.
                p = root / "mcp" / "mcp-auth.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('{"srv": {"serverUrl": "https://example/mcp", "tokens": {"accessToken": "tok"}}}\n', encoding="utf-8")

                c = RemoteMcpClient(url="https://example/mcp", headers={}, server_key="srv")
                hdrs = {k.lower(): v for k, v in (c.headers or {}).items()}
                self.assertEqual(hdrs.get("authorization"), "Bearer tok")
            finally:
                os.environ.pop("OPENAGENTIC_SDK_HOME", None)


if __name__ == "__main__":
    unittest.main()
