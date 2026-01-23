import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.edit import EditTool


class TestEditAnchors(unittest.TestCase):
    def test_edit_requires_before_after_match(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("aaa\nTARGET\nbbb\n", encoding="utf-8")
            tool = EditTool()

            with self.assertRaises(ValueError):
                tool.run_sync(
                    {"file_path": str(p), "old": "TARGET", "new": "OK", "before": "nope", "after": "bbb"},
                    ToolContext(cwd=str(root)),
                )

            out = tool.run_sync(
                {"file_path": str(p), "old": "TARGET", "new": "OK", "before": "aaa", "after": "bbb"},
                ToolContext(cwd=str(root)),
            )
            self.assertIn("replacements", out)
            self.assertEqual(p.read_text(encoding="utf-8"), "aaa\nOK\nbbb\n")


if __name__ == "__main__":
    unittest.main()

