import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestJsToolsLoading(unittest.TestCase):
    def test_js_tools_default_deny(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".opencode" / "tools").mkdir(parents=True)
            (root / ".opencode" / "tools" / "hello.ts").write_text(
                """\
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "hello tool",
  args: {
    name: tool.schema.string().default("world"),
  },
  async execute(args) {
    return `hello ${args.name}`
  },
})
""",
                encoding="utf-8",
            )

            os.environ["RIGHTCODE_API_KEY"] = "x"
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="deny")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)

            self.assertNotIn("hello", opts.tools.names())

    def test_js_tools_loads_when_enabled_in_config(self) -> None:
        from openagentic_cli.config import build_options
        from openagentic_sdk.tools.base import ToolContext

        with TemporaryDirectory() as td:
            root = Path(td)
            (root / ".opencode" / "tools").mkdir(parents=True)
            (root / ".opencode" / "tools" / "multi.ts").write_text(
                """\
import { tool } from "@opencode-ai/plugin"

export default tool({
  description: "default export tool",
  args: { x: tool.schema.number().default(2) },
  async execute(args) {
    return args.x * 2
  },
})

export const extra = tool({
  description: "extra export tool",
  args: { y: tool.schema.number().default(3) },
  async execute(args) {
    return args.y + 1
  },
})
""",
                encoding="utf-8",
            )
            (root / "opencode.json").write_text(
                '{"experimental": {"js_tools": true}}\n',
                encoding="utf-8",
            )

            os.environ["RIGHTCODE_API_KEY"] = "x"
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="deny")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)

            names = opts.tools.names()
            self.assertIn("multi", names)
            self.assertIn("multi_extra", names)

            # Smoke-test execution via the tool wrapper.
            tool_default = opts.tools.get("multi")
            out0 = tool_default.run_sync({"x": 4}, ctx=ToolContext(cwd=str(root), project_dir=str(root)))
            self.assertEqual(out0.get("output"), 8)
            tool_extra = opts.tools.get("multi_extra")
            out1 = tool_extra.run_sync({"y": 10}, ctx=ToolContext(cwd=str(root), project_dir=str(root)))
            self.assertEqual(out1.get("output"), 11)


if __name__ == "__main__":
    unittest.main()
