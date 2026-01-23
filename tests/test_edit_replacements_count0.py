import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.edit import EditTool


class TestEditCountZero(unittest.TestCase):
    def test_count_zero_replaces_all(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x x x", encoding="utf-8")
            tool = EditTool()
            out = tool.run_sync(
                {"file_path": str(p), "old": "x", "new": "y", "count": 0},
                ToolContext(cwd=str(root)),
            )
            self.assertEqual(p.read_text(encoding="utf-8"), "y y y")
            self.assertEqual(out["replacements"], 3)


if __name__ == "__main__":
    unittest.main()

