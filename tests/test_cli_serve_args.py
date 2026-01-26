import unittest


class TestCliServeArgs(unittest.TestCase):
    def test_parser_accepts_serve(self) -> None:
        from openagentic_cli.args import parse_args

        ns = parse_args(["serve", "--host", "127.0.0.1", "--port", "4097"])
        self.assertEqual(ns.command, "serve")
        self.assertEqual(ns.host, "127.0.0.1")
        self.assertEqual(ns.port, 4097)


if __name__ == "__main__":
    unittest.main()
