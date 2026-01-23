import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.read import ReadTool


class TestReadToolOffsetZero(unittest.TestCase):
    def test_offset_zero_treated_as_start(self) -> None:
        tool = ReadTool()
        with TemporaryDirectory() as td:
            p = Path(td) / "x.txt"
            p.write_text("a\nb\n", encoding="utf-8")
            out = tool.run_sync({"file_path": str(p), "offset": 0, "limit": 1}, ToolContext(cwd=str(td)))
            self.assertEqual(out["lines_returned"], 1)
            self.assertIn("1: a", out["content"])


if __name__ == "__main__":
    unittest.main()

