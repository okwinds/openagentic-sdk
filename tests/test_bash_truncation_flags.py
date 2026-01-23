import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.bash import BashTool


class TestBashTruncation(unittest.TestCase):
    def test_stdout_truncation_flag(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            tool = BashTool(max_output_bytes=10, timeout_s=5.0)
            out = tool.run_sync({"command": "printf '12345678901234567890'"}, ToolContext(cwd=str(root)))
            self.assertTrue(out["stdout_truncated"])


if __name__ == "__main__":
    unittest.main()

