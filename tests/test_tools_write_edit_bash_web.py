import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.bash import BashTool
from open_agent_sdk.tools.edit import EditTool
from open_agent_sdk.tools.web_fetch import WebFetchTool
from open_agent_sdk.tools.web_search_tavily import WebSearchTool
from open_agent_sdk.tools.write import WriteTool


class TestMoreTools(unittest.TestCase):
    def test_write_creates_file(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = WriteTool()
            out = tool.run_sync({"file_path": "a.txt", "content": "hi", "overwrite": False}, ToolContext(cwd=str(root)))
            self.assertTrue((root / "a.txt").exists())
            self.assertEqual(out["bytes_written"], 2)

    def test_edit_replaces_text(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("hello world", encoding="utf-8")
            tool = EditTool()
            out = tool.run_sync({"file_path": str(p), "old": "world", "new": "there", "count": 1}, ToolContext(cwd=str(root)))
            self.assertEqual(p.read_text(encoding="utf-8"), "hello there")
            self.assertEqual(out["replacements"], 1)

    def test_bash_runs_command(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = BashTool(timeout_s=5.0)
            out = tool.run_sync({"command": "echo hello"}, ToolContext(cwd=str(root)))
            self.assertEqual(out["exit_code"], 0)
            self.assertIn("hello", out["stdout"])

    def test_web_fetch_uses_transport(self) -> None:
        def transport(url, headers):
            return 200, {"content-type": "text/plain"}, b"ok"

        tool = WebFetchTool(transport=transport, allow_private_networks=True)
        out = tool.run_sync({"url": "https://example.com"}, ToolContext(cwd="/"))
        self.assertEqual(out["status"], 200)
        self.assertEqual(out["text"], "ok")

    def test_web_search_tavily_uses_transport(self) -> None:
        os.environ["TAVILY_API_KEY"] = "test"

        def transport(url, headers, payload):
            return {"results": [{"title": "t", "url": "u", "content": "c"}]}

        tool = WebSearchTool(transport=transport)
        out = tool.run_sync({"query": "x", "max_results": 5}, ToolContext(cwd="/"))
        self.assertEqual(out["results"][0]["source"], "tavily")


if __name__ == "__main__":
    unittest.main()

