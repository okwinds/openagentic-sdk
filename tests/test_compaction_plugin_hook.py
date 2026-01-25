import unittest


class TestCompactionPluginHook(unittest.IsolatedAsyncioTestCase):
    async def test_plugin_can_inject_compaction_prompt(self) -> None:
        import os
        import sys
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from openagentic_sdk import query
        from openagentic_sdk.options import CompactionOptions, OpenAgenticOptions
        from openagentic_sdk.permissions.gate import PermissionGate
        from openagentic_sdk.providers.base import ModelOutput
        from openagentic_sdk.sessions.store import FileSessionStore

        class ProviderOverflowThenSummarize:
            name = "fake-legacy"

            def __init__(self) -> None:
                self.calls = 0

            async def complete(self, *, model, messages, tools=(), api_key=None):
                _ = (model, tools, api_key)
                self.calls += 1
                if self.calls == 1:
                    return ModelOutput(assistant_text="hi", tool_calls=(), usage={"input_tokens": 9000, "output_tokens": 10, "total_tokens": 9010}, raw=None)
                if self.calls == 2:
                    # The last user message should be the injected prompt.
                    last_user = next(m for m in reversed(messages) if isinstance(m, dict) and m.get("role") == "user")
                    if "PLUGIN_PROMPT" not in (last_user.get("content") or ""):
                        raise AssertionError(f"expected plugin prompt, got: {last_user!r}")
                    return ModelOutput(assistant_text="summary", tool_calls=(), usage={"total_tokens": 1}, raw=None)
                return ModelOutput(assistant_text="done", tool_calls=(), usage={"total_tokens": 1}, raw=None)

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            plugin_path = root / "my_plugin.py"
            plugin_path.write_text(
                """\
from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher


async def _hook(payload: dict):
    _ = payload
    return HookDecision(override_tool_output={"context": ["CTX"], "prompt": "PLUGIN_PROMPT"})


def register(registry):
    registry.add_hooks(HookEngine(session_compacting=[HookMatcher(name="c", tool_name_pattern="*", hook=_hook)]))
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
                from openagentic_cli.config import build_options

                opts = build_options(cwd=str(root), project_dir=str(root), permission_mode="bypass")
            finally:
                os.environ.pop("RIGHTCODE_API_KEY", None)
                os.environ.pop("OPENCODE_CONFIG_DIR", None)
                os.environ.pop("OPENCODE_TEST_HOME", None)

            # Override provider and compaction settings for the test run.
            provider = ProviderOverflowThenSummarize()
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
                hooks=opts.hooks,
                compaction=CompactionOptions(auto=True, prune=False, context_limit=9000, global_output_cap=4096),
            )

            events = []
            async for e in query(prompt="hello", options=options):
                events.append(e)
            self.assertTrue(any(getattr(e, "type", "") == "assistant.message" and getattr(e, "is_summary", False) for e in events))


if __name__ == "__main__":
    unittest.main()
