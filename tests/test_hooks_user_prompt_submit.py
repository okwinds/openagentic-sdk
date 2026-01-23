import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.hooks.models import HookDecision, HookMatcher
from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class CapturingProvider:
    name = "noop"

    def __init__(self) -> None:
        self.last_messages = []

    async def complete(self, *, model, messages, tools=(), api_key=None):
        _ = (model, tools, api_key)
        self.last_messages = list(messages)
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestUserPromptSubmitHook(unittest.IsolatedAsyncioTestCase):
    async def test_user_prompt_submit_can_rewrite_prompt(self) -> None:
        async def rewrite(inp):
            _ = inp
            return HookDecision(override_prompt="rewritten", action="rewrite_prompt")

        hooks = HookEngine(user_prompt_submit=[HookMatcher(name="rw", tool_name_pattern="*", hook=rewrite)])

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            provider = CapturingProvider()
            options = OpenAgentOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                hooks=hooks,
            )
            import openagentic_sdk

            async for e in openagentic_sdk.query(prompt="original", options=options):
                if getattr(e, "type", None) == "result":
                    break

            self.assertEqual(provider.last_messages[-1]["role"], "user")
            self.assertEqual(provider.last_messages[-1]["content"], "rewritten")


if __name__ == "__main__":
    unittest.main()

