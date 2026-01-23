import asyncio
import io
import unittest

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider


class _TtyStringIO(io.StringIO):
    def isatty(self) -> bool:  # pragma: no cover
        return False


class TestCliReplBuiltinCwd(unittest.TestCase):
    def test_cwd_question_is_answered_locally(self) -> None:
        from openagentic_cli.repl import run_chat
        from openagentic_cli.style import StyleConfig

        opts = OpenAgentOptions(
            provider=OpenAICompatibleProvider(base_url="https://example.invalid"),
            model="gpt-5.2",
            api_key=None,
            cwd="C:\\proj",
            permission_gate=PermissionGate(permission_mode="deny"),
            setting_sources=[],
        )

        stdin = _TtyStringIO("当前目录是？\n/exit\n")
        stdout = _TtyStringIO()
        code = asyncio.run(run_chat(opts, color_config=StyleConfig(color="never"), debug=False, stdin=stdin, stdout=stdout))
        self.assertEqual(code, 0)
        self.assertIn("当前目录：C:\\proj", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

