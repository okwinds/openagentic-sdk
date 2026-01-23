import unittest

from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher


class TestMessageRewriteFlag(unittest.IsolatedAsyncioTestCase):
    async def test_override_messages_ignored_when_flag_off(self) -> None:
        async def rewrite(_input):
            return HookDecision(
                override_messages=[{"role": "system", "content": "x"}],
                action="rewrite_messages",
            )

        engine = HookEngine(
            before_model_call=[HookMatcher(name="rw", tool_name_pattern="*", hook=rewrite)],
            enable_message_rewrite_hooks=False,
        )
        msgs, _events, decision = await engine.run_before_model_call(messages=[{"role": "user", "content": "hi"}], context={})
        self.assertEqual(msgs[0]["role"], "user")
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()

