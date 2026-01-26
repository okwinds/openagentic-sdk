import os
import time
import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory


class RecordingResponsesProvider:
    name = "openai"

    def __init__(self) -> None:
        self.calls = []

    async def complete(self, *, model, input, tools=(), api_key=None, previous_response_id=None, store=True, instructions=None, include=()):
        # Record raw call kwargs for assertions.
        self.calls.append(
            {
                "model": model,
                "input": list(input),
                "instructions": instructions,
                "previous_response_id": previous_response_id,
                "store": store,
            }
        )
        from openagentic_sdk.providers.base import ModelOutput

        return ModelOutput(assistant_text="ok", tool_calls=[], response_id="r1")


class TestCodexPromptWiring(unittest.IsolatedAsyncioTestCase):
    async def test_codex_session_uses_instructions_and_user_role_system(self) -> None:
        import openagentic_sdk
        from openagentic_sdk.auth import OAuthAuth, set_auth
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.permissions.gate import PermissionGate
        from openagentic_sdk.sessions.store import FileSessionStore

        with TemporaryDirectory() as td:
            root = Path(td)
            # Keep auth store hermetic.
            env = {
                "OPENAGENTIC_SDK_HOME": str(root / "home"),
                "OPENCODE_TEST_HOME": str(root / "home"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                set_auth("openai", OAuthAuth(refresh="r", access="a", expires=int(time.time()) + 3600))

                store = FileSessionStore(root_dir=root)
                provider = RecordingResponsesProvider()
                options = OpenAgenticOptions(
                    provider=provider,
                    model="gpt-5.2",
                    api_key="x",
                    cwd=str(root),
                    session_store=store,
                    permission_gate=PermissionGate(permission_mode="bypass"),
                    setting_sources=["project"],
                    project_dir=str(root),
                )

                async for _ in openagentic_sdk.query(prompt="hi", options=options):
                    pass

                self.assertTrue(provider.calls)
                call0 = provider.calls[0]
                self.assertIsInstance(call0.get("instructions"), str)
                self.assertTrue(str(call0.get("instructions")).strip())

                inp0 = call0["input"][0]
                self.assertEqual(inp0.get("role"), "user")


if __name__ == "__main__":
    unittest.main()
