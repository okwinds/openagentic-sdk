import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestPluginsLoading(unittest.TestCase):
    def test_loads_plugins_from_opencode_config_and_merges_hooks(self) -> None:
        from openagentic_cli.config import build_options

        with TemporaryDirectory() as td:
            root = Path(td)
            plugin_path = root / "my_plugin.py"
            plugin_path.write_text(
                """\
from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher


async def _hook(payload: dict):
    return HookDecision(action=\"plugin_ran\")


def register(registry):
    registry.add_before_model_call(HookMatcher(name=\"p\", tool_name_pattern=\"*\", hook=_hook))
""",
                encoding="utf-8",
            )

            (root / "opencode.json").write_text(
                '{"plugin": ["file://my_plugin.py"]}\n',
                encoding="utf-8",
            )

            os.environ["RIGHTCODE_API_KEY"] = "x"
            os.environ["OPENCODE_CONFIG_DIR"] = str(root / "empty-global")
            os.environ["OPENCODE_TEST_HOME"] = str(root / "home")
            try:
                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="bypass")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)

            names = [m.name for m in opts.hooks.before_model_call]
            self.assertIn("p", names)


if __name__ == "__main__":
    unittest.main()
