import unittest
from unittest import mock


class TestConsoleRunHelpers(unittest.TestCase):
    def test_console_query_non_debug_exits_cleanly(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.console.run import console_query
        from open_agent_sdk.options import OpenAgentOptions
        from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider

        options = OpenAgentOptions(provider=OpenAICompatibleProvider(), model="m", api_key="k", cwd=".")

        async def boom(*_args, **_kwargs):  # noqa: ANN001
            raise RuntimeError("boom")
            if False:  # pragma: no cover
                yield  # noqa: B018

        with mock.patch("open_agent_sdk.console.run.query", boom):
            with self.assertRaises(SystemExit) as ctx:
                import asyncio

                asyncio.run(console_query(prompt="x", options=options, renderer=ConsoleRenderer(debug=False)))
        self.assertIn("boom", str(ctx.exception))

    def test_console_query_debug_re_raises(self) -> None:
        from open_agent_sdk.console import ConsoleRenderer
        from open_agent_sdk.console.run import console_query
        from open_agent_sdk.options import OpenAgentOptions
        from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider

        options = OpenAgentOptions(provider=OpenAICompatibleProvider(), model="m", api_key="k", cwd=".")

        async def boom(*_args, **_kwargs):  # noqa: ANN001
            raise RuntimeError("boom")
            if False:  # pragma: no cover
                yield  # noqa: B018

        with mock.patch("open_agent_sdk.console.run.query", boom):
            with self.assertRaises(RuntimeError):
                import asyncio

                asyncio.run(console_query(prompt="x", options=options, renderer=ConsoleRenderer(debug=True)))


if __name__ == "__main__":
    unittest.main()
