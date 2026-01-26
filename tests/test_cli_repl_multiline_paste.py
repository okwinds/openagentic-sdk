import io
import os
import unittest


class TestCliReplMultilinePaste(unittest.TestCase):
    def test_read_turn_single_line(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        turn = read_repl_turn(io.StringIO("hello\n"))
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "hello")
        self.assertFalse(turn.is_paste)

    def test_read_turn_bracketed_paste_multiple_lines(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        s = "\x1b[200~a\n" "b\n" "c\x1b[201~\n"
        turn = read_repl_turn(io.StringIO(s))
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "a\nb\nc")
        self.assertTrue(turn.is_paste)

    def test_read_turn_bracketed_paste_same_line(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        s = "\x1b[200~one line\x1b[201~\n"
        turn = read_repl_turn(io.StringIO(s))
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "one line")
        self.assertTrue(turn.is_paste)

    def test_read_turn_paste_does_not_strip_internal_newlines(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        s = "\x1b[200~x\n\n y\x1b[201~\n"
        turn = read_repl_turn(io.StringIO(s))
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "x\n\n y")
        self.assertTrue(turn.is_paste)

    def test_read_turn_manual_paste_mode_until_end(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        stdin = io.StringIO("line1\nline2\n/end\n")
        turn = read_repl_turn(stdin, paste_mode=True)
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "line1\nline2")
        self.assertTrue(turn.is_paste)

    def test_read_turn_manual_paste_mode_strips_bracketed_paste_markers(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        s = "\x1b[200~line1\nline2\x1b[201~\n/end\n"
        turn = read_repl_turn(io.StringIO(s), paste_mode=True)
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "line1\nline2")
        self.assertTrue(turn.is_paste)
        self.assertTrue(turn.is_manual_paste)

    def test_read_turn_manual_paste_mode_end_with_whitespace(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        stdin = io.StringIO("line1\n/end  \n")
        turn = read_repl_turn(stdin, paste_mode=True)
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "line1")
        self.assertTrue(turn.is_paste)
        self.assertTrue(turn.is_manual_paste)

    def test_read_turn_manual_paste_mode_eof_returns_none(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        turn = read_repl_turn(io.StringIO(""), paste_mode=True)
        self.assertIsNone(turn)

    def test_read_turn_manual_paste_mode_eof_after_lines(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        turn = read_repl_turn(io.StringIO("line1\n"), paste_mode=True)
        self.assertIsNotNone(turn)
        assert turn is not None
        self.assertEqual(turn.text, "line1")
        self.assertTrue(turn.is_paste)
        self.assertTrue(turn.is_manual_paste)

    def test_read_turn_tty_buffered_multiline_coalesces_without_markers(self) -> None:
        from openagentic_cli.repl import read_repl_turn

        rfd, wfd = os.pipe()
        try:
            os.write(wfd, b"line1\nline2\nline3\n")
            os.close(wfd)

            with os.fdopen(rfd, "r", encoding="utf-8") as r:
                r.isatty = lambda: True  # type: ignore[method-assign]
                turn = read_repl_turn(r)
                self.assertIsNotNone(turn)
                assert turn is not None
                self.assertEqual(turn.text, "line1\nline2\nline3")
                self.assertTrue(turn.is_paste)
        finally:
            try:
                os.close(wfd)
            except OSError:
                pass
            try:
                os.close(rfd)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
