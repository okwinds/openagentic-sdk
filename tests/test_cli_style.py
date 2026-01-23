import os
import unittest


class TestCliStyle(unittest.TestCase):
    def test_no_color_env_disables_color(self) -> None:
        from open_agent_cli.style import StyleConfig, should_colorize

        os.environ["NO_COLOR"] = "1"
        try:
            self.assertFalse(should_colorize(StyleConfig(color="auto"), isatty=True, platform="linux"))
        finally:
            os.environ.pop("NO_COLOR", None)

    def test_color_always_enables_color(self) -> None:
        from open_agent_cli.style import StyleConfig, should_colorize

        self.assertTrue(should_colorize(StyleConfig(color="always"), isatty=False, platform="linux"))


if __name__ == "__main__":
    unittest.main()

