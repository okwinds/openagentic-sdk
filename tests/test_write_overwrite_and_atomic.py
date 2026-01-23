import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from open_agent_sdk.tools.base import ToolContext
from open_agent_sdk.tools.write import WriteTool


class TestWriteTool(unittest.TestCase):
    def test_overwrite_false_raises(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("x", encoding="utf-8")
            tool = WriteTool()
            with self.assertRaises(FileExistsError):
                tool.run_sync(
                    {"file_path": str(p), "content": "y", "overwrite": False},
                    ToolContext(cwd=str(root)),
                )

    def test_atomic_write_uses_tmp_and_cleans_up(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = WriteTool()

            write_calls: list[str] = []
            orig_write_text = Path.write_text

            def wrapped_write_text(self: Path, data: str, *args, **kwargs):
                write_calls.append(self.name)
                return orig_write_text(self, data, *args, **kwargs)

            with patch("pathlib.Path.write_text", new=wrapped_write_text):
                tool.run_sync(
                    {"file_path": "a.txt", "content": "hi", "overwrite": True},
                    ToolContext(cwd=str(root)),
                )

            self.assertTrue(any(name.endswith(".tmp") for name in write_calls), write_calls)
            tmp_like = [x for x in root.iterdir() if x.name.endswith(".tmp")]
            self.assertEqual(tmp_like, [])


if __name__ == "__main__":
    unittest.main()

