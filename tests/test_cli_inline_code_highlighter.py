import unittest


class TestCliInlineCodeHighlighter(unittest.TestCase):
    def test_highlights_inline_backticks_not_fences(self) -> None:
        from open_agent_cli.style import InlineCodeHighlighter

        h = InlineCodeHighlighter(enabled=True)
        s1 = h.feed("hi `x` ok\n```py\nprint(1)\n```\n")
        self.assertIn("\x1b[34m`x`\x1b[39m", s1)
        self.assertIn("```py", s1)

    def test_streaming_chunks_keep_state(self) -> None:
        from open_agent_cli.style import InlineCodeHighlighter

        h = InlineCodeHighlighter(enabled=True)
        a = h.feed("hi `x")
        b = h.feed("` ok")
        self.assertIn("\x1b[34m", a + b)
        self.assertIn("\x1b[39m", a + b)


if __name__ == "__main__":
    unittest.main()

