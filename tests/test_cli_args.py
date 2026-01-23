import unittest


class TestCliArgs(unittest.TestCase):
    def test_resume_parses_session_id(self) -> None:
        from open_agent_cli.args import parse_args

        ns = parse_args(["resume", "abc123"])
        self.assertEqual(ns.command, "resume")
        self.assertEqual(ns.session_id, "abc123")


if __name__ == "__main__":
    unittest.main()

