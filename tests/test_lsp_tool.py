from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from openagentic_sdk.tools.lsp import LspTool
from openagentic_sdk.tools.base import ToolContext


class TestLspTool(unittest.IsolatedAsyncioTestCase):
    async def test_lsp_hover_definition_and_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Keep tests hermetic w.r.t. user global config.
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "global-opencode")

            fixture = Path(__file__).resolve().parent / "fixtures" / "lsp_stub_server.py"
            self.assertTrue(fixture.exists())

            (root / "a.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "opencode.json").write_text(
                """
{
  "lsp": {
    "stub": {
      "command": ["%s", "%s"],
      "extensions": [".py"]
    }
  }
}
"""
                % (sys.executable.replace("\\", "\\\\"), str(fixture).replace("\\", "\\\\")),
                encoding="utf-8",
            )

            tool = LspTool()
            ctx = ToolContext(cwd=str(root), project_dir=str(root))

            out1 = await tool.run({"operation": "hover", "filePath": "a.py", "line": 1, "character": 1}, ctx)
            self.assertIn("stub hover", out1.get("output", ""))

            out2 = await tool.run({"operation": "goToDefinition", "filePath": "a.py", "line": 1, "character": 1}, ctx)
            md2 = out2.get("metadata")
            self.assertIsInstance(md2, dict)
            self.assertIsInstance(md2.get("result"), list)

            out3 = await tool.run({"operation": "documentSymbol", "filePath": "a.py", "line": 1, "character": 1}, ctx)
            md3 = out3.get("metadata")
            self.assertIsInstance(md3, dict)
            res3 = md3.get("result")
            self.assertTrue(res3 is None or isinstance(res3, list))

    async def test_lsp_errors_without_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "global-opencode")
            (root / "a.py").write_text("print('hi')\n", encoding="utf-8")

            tool = LspTool()
            ctx = ToolContext(cwd=str(root), project_dir=str(root))
            with self.assertRaises(RuntimeError):
                await tool.run({"operation": "hover", "filePath": "a.py", "line": 1, "character": 1}, ctx)


if __name__ == "__main__":
    unittest.main()
