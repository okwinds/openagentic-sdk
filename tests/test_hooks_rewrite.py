import unittest

from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher


class TestHooks(unittest.IsolatedAsyncioTestCase):
    async def test_pre_tool_use_can_rewrite_tool_input(self) -> None:
        async def rewrite(input_data):
            tool_input = dict(input_data["tool_input"])
            tool_input["file_path"] = "rewritten.txt"
            return HookDecision(override_tool_input=tool_input, action="rewrite")

        engine = HookEngine(
            pre_tool_use=[HookMatcher(name="rewrite-read", tool_name_pattern="Read", hook=rewrite)],
        )
        tool_input, hook_events, decision = await engine.run_pre_tool_use(
            tool_name="Read",
            tool_input={"file_path": "original.txt"},
            context={},
        )
        self.assertIsNone(decision)
        self.assertEqual(tool_input["file_path"], "rewritten.txt")
        self.assertEqual(len(hook_events), 1)
        self.assertEqual(hook_events[0].hook_point, "PreToolUse")


if __name__ == "__main__":
    unittest.main()

