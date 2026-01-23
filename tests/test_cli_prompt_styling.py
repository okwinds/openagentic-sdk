import asyncio
import io
import os
import unittest

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider


class _TtyStringIO(io.StringIO):
    def isatty(self) -> bool:  # pragma: no cover
        return True


class TestCliPromptStyling(unittest.TestCase):
    def test_prompt_uses_gray_background_when_color_enabled(self) -> None:
        from openagentic_cli.repl import run_chat
        from openagentic_cli.style import StyleConfig

        os.environ.pop("NO_COLOR", None)
        os.environ["COLUMNS"] = "40"
        os.environ["LINES"] = "10"
        opts = OpenAgentOptions(
            provider=OpenAICompatibleProvider(base_url="https://example.invalid"),
            model="gpt-5.2",
            api_key=None,
            cwd="C:\\proj",
            permission_gate=PermissionGate(permission_mode="deny"),
            setting_sources=[],
        )
        stdin = io.StringIO("/exit\n")
        stdout = _TtyStringIO()
        code = asyncio.run(run_chat(opts, color_config=StyleConfig(color="always"), debug=False, stdin=stdin, stdout=stdout))
        self.assertEqual(code, 0)
        self.assertIn("\x1b[100m", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

