import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher
from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.providers.base import ModelOutput
from open_agent_sdk.sessions.store import FileSessionStore


class NoopProvider:
    name = "noop"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, model, messages, tools=(), api_key=None):
        self.calls += 1
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestHooksModelPoints(unittest.IsolatedAsyncioTestCase):
    async def test_before_model_hook_can_block(self) -> None:
        async def block(_input):
            return HookDecision(block=True, block_reason="nope", action="block")

        hooks = HookEngine(before_model_call=[HookMatcher(name="block", tool_name_pattern="*", hook=block)])

        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=NoopProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                hooks=hooks,
            )
            import open_agent_sdk

            events = []
            async for e in open_agent_sdk.query(prompt="hi", options=options):
                events.append(e)
                if getattr(e, "type", None) == "result":
                    break
            r = next(e for e in events if getattr(e, "type", None) == "result")
            self.assertIn("blocked", (r.stop_reason or "").lower())


if __name__ == "__main__":
    unittest.main()

