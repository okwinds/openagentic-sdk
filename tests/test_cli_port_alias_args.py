import unittest


class TestCliPortAliasArgs(unittest.TestCase):
    def test_top_level_port_parses_without_command(self) -> None:
        from openagentic_cli.args import parse_args

        ns = parse_args(["--port", "1234"])
        self.assertIsNone(getattr(ns, "command", None))
        self.assertEqual(ns.port, 1234)


if __name__ == "__main__":
    unittest.main()
