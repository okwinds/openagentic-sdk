import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestJsPluginsLoading(unittest.TestCase):
    def test_js_plugin_tools_default_deny_and_no_crash(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            plugin_path = root / "my_plugin.ts"
            plugin_path.write_text(
                """\
import { tool } from "@opencode-ai/plugin"

export default async function plugin(_input) {
  return {
    tool: {
      plugin_echo: tool({
        description: "plugin echo",
        args: { msg: tool.schema.string().default("hi") },
        async execute(args) {
          return `echo:${args.msg}`
        },
      }),
    },
  }
}
""",
                encoding="utf-8",
            )
            (root / "opencode.json").write_text(
                '{"plugin": ["file://my_plugin.ts"]}\n',
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

            # JS plugins are disabled by default, but the presence of a JS plugin spec
            # must not crash the CLI.
            self.assertNotIn("plugin_echo", opts.tools.names())

    def test_js_plugin_tools_load_when_enabled(self) -> None:
        from openagentic_cli.config import build_options
        from openagentic_sdk.tools.base import ToolContext

        with TemporaryDirectory() as td:
            root = Path(td)
            plugin_path = root / "my_plugin.ts"
            plugin_path.write_text(
                """\
import { tool } from "@opencode-ai/plugin"

export default async function plugin(_input) {
  return {
    tool: {
      plugin_add: tool({
        description: "plugin add",
        args: { a: tool.schema.number().default(1), b: tool.schema.number().default(2) },
        async execute(args) {
          return args.a + args.b
        },
      }),
    },
  }
}
""",
                encoding="utf-8",
            )
            (root / "opencode.json").write_text(
                '{"experimental": {"js_plugins": true}, "plugin": ["file://my_plugin.ts"]}\n',
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

            self.assertIn("plugin_add", opts.tools.names())

            t = opts.tools.get("plugin_add")
            out = t.run_sync({"a": 10, "b": 5}, ctx=ToolContext(cwd=str(root), project_dir=str(root)))
            self.assertEqual(out.get("output"), 15)


if __name__ == "__main__":
    unittest.main()
