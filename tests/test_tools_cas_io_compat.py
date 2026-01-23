import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.bash import BashTool
from openagentic_sdk.tools.edit import EditTool
from openagentic_sdk.tools.glob import GlobTool
from openagentic_sdk.tools.grep import GrepTool
from openagentic_sdk.tools.read import ReadTool
from openagentic_sdk.tools.write import WriteTool


class TestToolCasCompat(unittest.TestCase):
    def test_read_offset_limit_returns_numbered_content(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("l1\nl2\nl3\n", encoding="utf-8")
            tool = ReadTool()
            out = tool.run_sync({"file_path": str(p), "offset": 2, "limit": 1}, ToolContext(cwd=str(root)))
            self.assertEqual(out["total_lines"], 3)
            self.assertEqual(out["lines_returned"], 1)
            self.assertTrue(str(out["content"]).startswith("2: "))

    def test_write_returns_message(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = WriteTool()
            out = tool.run_sync({"file_path": "a.txt", "content": "hi", "overwrite": False}, ToolContext(cwd=str(root)))
            self.assertIn("message", out)
            self.assertEqual(out["bytes_written"], 2)

    def test_edit_accepts_old_string_new_string_replace_all(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x x x", encoding="utf-8")
            tool = EditTool()
            out = tool.run_sync(
                {"file_path": str(p), "old_string": "x", "new_string": "y", "replace_all": True},
                ToolContext(cwd=str(root)),
            )
            self.assertEqual(p.read_text(encoding="utf-8"), "y y y")
            self.assertEqual(out["replacements"], 3)

    def test_bash_accepts_timeout_ms_and_returns_output_alias(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = BashTool(timeout_s=5.0)
            out = tool.run_sync({"command": "echo hello", "timeout": 2000}, ToolContext(cwd=str(root)))
            self.assertEqual(out["exitCode"], 0)
            self.assertIn("hello", out["output"])

    def test_glob_accepts_path_alias_and_returns_count(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("a", encoding="utf-8")
            tool = GlobTool()
            out = tool.run_sync({"pattern": "**/*.txt", "path": str(root)}, ToolContext(cwd=str(root)))
            self.assertEqual(out["count"], 1)

    def test_grep_files_with_matches_mode(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
            tool = GrepTool()
            out = tool.run_sync({"query": "hello", "file_glob": "**/*.txt", "path": str(root), "mode": "files_with_matches"}, ToolContext(cwd=str(root)))
            self.assertEqual(out["count"], 1)
            self.assertEqual(out["files"], [str(root / "a.txt")])

    def test_read_accepts_file_path_alias_filePath(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("hello", encoding="utf-8")
            tool = ReadTool()
            out = tool.run_sync({"filePath": str(p)}, ToolContext(cwd=str(root)))
            self.assertIn("hello", out["content"])

    def test_write_accepts_file_path_alias_filePath(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = WriteTool()
            out = tool.run_sync({"filePath": "a.txt", "content": "hi", "overwrite": True}, ToolContext(cwd=str(root)))
            self.assertEqual(Path(out["file_path"]).read_text(encoding="utf-8"), "hi")

    def test_edit_accepts_oldString_newString_replaceAll(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x x x", encoding="utf-8")
            tool = EditTool()
            out = tool.run_sync(
                {"filePath": str(p), "oldString": "x", "newString": "y", "replaceAll": True},
                ToolContext(cwd=str(root)),
            )
            self.assertEqual(p.read_text(encoding="utf-8"), "y y y")
            self.assertEqual(out["replacements"], 3)

    def test_bash_accepts_workdir_override(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            d1 = root / "d1"
            d2 = root / "d2"
            d1.mkdir()
            d2.mkdir()
            tool = BashTool(timeout_s=5.0)
            out = tool.run_sync({"command": "pwd", "workdir": str(d2)}, ToolContext(cwd=str(d1)))
            self.assertIn(str(d2), out["stdout"])


if __name__ == "__main__":
    unittest.main()
