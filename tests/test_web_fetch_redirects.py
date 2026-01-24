import unittest

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.web_fetch import WebFetchTool


class TestWebFetchRedirects(unittest.TestCase):
    def test_redirect_to_private_network_is_blocked(self) -> None:
        def transport(url, headers):
            _ = headers
            if url == "https://example.com":
                return 302, {"location": "http://127.0.0.1/private"}, b""
            raise AssertionError(f"unexpected url: {url}")

        tool = WebFetchTool(transport=transport, allow_private_networks=False)
        with self.assertRaises(ValueError):
            tool.run_sync({"url": "https://example.com"}, ToolContext(cwd="/"))

    def test_relative_redirect_is_followed(self) -> None:
        def transport(url, headers):
            _ = headers
            if url == "https://example.com/start":
                return 302, {"Location": "/next"}, b""
            if url == "https://example.com/next":
                return 200, {"content-type": "text/plain"}, b"ok"
            raise AssertionError(f"unexpected url: {url}")

        tool = WebFetchTool(transport=transport, allow_private_networks=True)
        out = tool.run_sync({"url": "https://example.com/start"}, ToolContext(cwd="/"))
        self.assertEqual(out["status"], 200)
        self.assertEqual(out["text"], "ok")
        self.assertEqual(out["requested_url"], "https://example.com/start")
        self.assertEqual(out["final_url"], "https://example.com/next")

    def test_max_redirects_is_enforced(self) -> None:
        def transport(url, headers):
            _ = headers
            if url == "https://example.com/a":
                return 302, {"location": "/b"}, b""
            if url == "https://example.com/b":
                return 302, {"location": "/c"}, b""
            raise AssertionError(f"unexpected url: {url}")

        tool = WebFetchTool(transport=transport, allow_private_networks=True, max_redirects=1)
        with self.assertRaises(ValueError):
            tool.run_sync({"url": "https://example.com/a"}, ToolContext(cwd="/"))


if __name__ == "__main__":
    unittest.main()
