import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestCustomToolsLoading(unittest.TestCase):
    def test_loads_custom_tools_from_opencode_tool_dirs(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".opencode" / "tools").mkdir(parents=True)
            (root / ".opencode" / "tools" / "hello.py").write_text(
                """\
from dataclasses import dataclass
from typing import Any, Mapping

from openagentic_sdk.tools.base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class HelloTool(Tool):
    name: str = "Hello"
    description: str = "hello tool"

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = (tool_input, ctx)
        return {"ok": True}


TOOLS = [HelloTool()]
""",
                encoding="utf-8",
            )

            os.environ["RIGHTCODE_API_KEY"] = "x"
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
            try:
                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="deny")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)

            self.assertIn("Hello", opts.tools.names())


if __name__ == "__main__":
    unittest.main()
