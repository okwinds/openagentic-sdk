import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk import query
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore


class LegacyProviderAsksSlashCommand:
    name = "legacy-slash"

    def __init__(self) -> None:
        self.calls: list[list[dict]] = []

    async def complete(self, *, model: str, messages, tools=(), api_key=None):
        msgs = list(messages)
        self.calls.append(msgs)

        # First call: ask runtime to execute SlashCommand.
        if len(self.calls) == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[
                    ToolCall(tool_use_id="sc_1", name="SlashCommand", arguments={"name": "hello", "args": "world foo"})
                ],
                usage={"total_tokens": 1},
                raw=None,
            )

        # Second call: ensure tool result contains rendered content.
        tool_msgs = [m for m in msgs if isinstance(m, dict) and m.get("role") == "tool"]
        self.assertTrue(tool_msgs)
        payload = json.loads(tool_msgs[-1].get("content") or "{}")
        content = payload.get("content")
        if not isinstance(content, str):
            raise AssertionError("expected rendered content string")
        self.assertIn("Hello world", content)
        self.assertIn("Args: world foo", content)
        self.assertIn("INCLUDED: filedata", content)
        self.assertIn("SHELL: shellout", content)

        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 2}, raw=None)

    def assertTrue(self, cond: bool) -> None:
        if not cond:
            raise AssertionError("assertTrue failed")

    def assertIn(self, needle: str, haystack: str) -> None:
        if needle not in haystack:
            raise AssertionError(f"expected {needle!r} in text")


class TestSlashCommandTemplating(unittest.IsolatedAsyncioTestCase):
    async def test_slash_command_expands_args_files_and_shell(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "input.txt").write_text("filedata", encoding="utf-8")

            # Highest-precedence command root for parity: .opencode/commands
            (root / ".opencode" / "commands").mkdir(parents=True)
            (root / ".opencode" / "commands" / "hello.md").write_text(
                """Hello $1
Args: $ARGUMENTS
INCLUDED: @input.txt
SHELL: !echo shellout
""",
                encoding="utf-8",
            )

            store = FileSessionStore(root_dir=root)
            provider = LegacyProviderAsksSlashCommand()
            options = OpenAgenticOptions(
                provider=provider,
                model="fake",
                api_key="x",
                cwd=str(root),
                project_dir=str(root),
                session_store=store,
                permission_gate=PermissionGate(permission_mode="bypass"),
            )

            evs = []
            async for e in query(prompt="run cmd", options=options):
                evs.append(e)

            self.assertTrue(any(getattr(e, "type", "") == "result" for e in evs))


if __name__ == "__main__":
    unittest.main()
