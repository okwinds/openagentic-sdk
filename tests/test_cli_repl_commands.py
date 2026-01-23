import unittest


class TestCliReplCommands(unittest.TestCase):
    def test_parse_repl_command(self) -> None:
        from openagentic_cli.repl import parse_repl_command

        self.assertEqual(parse_repl_command("/help"), ("help", ""))
        self.assertEqual(parse_repl_command("/skill main-process"), ("skill", "main-process"))


if __name__ == "__main__":
    unittest.main()

