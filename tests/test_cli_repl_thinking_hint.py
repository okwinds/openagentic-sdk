import asyncio
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput


class _Provider:
    name = "openai-compatible"

    async def complete(self, *, model, messages, tools=(), api_key=None):  # noqa: ANN001
        _ = (model, messages, tools, api_key)
        return ModelOutput(assistant_text="ok", tool_calls=())


class _TtyStringIO(io.StringIO):
    def isatty(self) -> bool:  # pragma: no cover
        return True


class TestCliReplThinkingHint(unittest.TestCase):
    def test_prints_thinking_hint_before_response(self) -> None:
        from openagentic_cli.repl import run_chat
        from openagentic_cli.style import StyleConfig

        with TemporaryDirectory() as td:
            opts = OpenAgenticOptions(
                provider=_Provider(),
                model="gpt-5.2",
                api_key=None,
                cwd="C:\\proj",
                permission_gate=PermissionGate(permission_mode="deny"),
                setting_sources=[],
                session_root=Path(td),
            )

            stdin = io.StringIO("hi\n/exit\n")
            stdout = _TtyStringIO()
            code = asyncio.run(run_chat(opts, color_config=StyleConfig(color="never"), debug=False, stdin=stdin, stdout=stdout))
            self.assertEqual(code, 0)
            s = stdout.getvalue()
            self.assertIn("thinking…", s)
            self.assertIn("ok", s)


if __name__ == "__main__":
    unittest.main()
