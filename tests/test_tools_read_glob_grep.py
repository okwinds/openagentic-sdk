import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.glob import GlobTool
from open_agent_sdk.tools.grep import GrepTool
from open_agent_sdk.tools.read import ReadTool
from open_agent_sdk.tools.registry import ToolRegistry
from open_agent_sdk.tools.base import ToolContext


class TestTools(unittest.TestCase):
    def test_read_tool_reads_file(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("hello", encoding="utf-8")
            tools = ToolRegistry([ReadTool()])
            out = tools.get("Read").run_sync({"file_path": str(p)}, ToolContext(cwd=str(root)))
            self.assertEqual(out["content"], "hello")

    def test_glob_tool_finds_files(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.md").write_text("b", encoding="utf-8")
            tools = ToolRegistry([GlobTool()])
            out = tools.get("Glob").run_sync({"pattern": "**/*.txt", "root": str(root)}, ToolContext(cwd=str(root)))
            self.assertEqual(out["matches"], [str(root / "a.txt")])

    def test_grep_tool_searches(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
            tools = ToolRegistry([GrepTool()])
            out = tools.get("Grep").run_sync(
                {"query": "hello", "file_glob": "**/*.txt", "root": str(root)},
                ToolContext(cwd=str(root)),
            )
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["line"], 1)


if __name__ == "__main__":
    unittest.main()

