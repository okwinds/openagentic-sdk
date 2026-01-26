import unittest


class TestCliGithubArgs(unittest.TestCase):
    def test_github_install_parses(self) -> None:
        from openagentic_cli.args import parse_args

        ns = parse_args(["github", "install", "--path", ".github/workflows/oa.yml", "--force"])
        self.assertEqual(ns.command, "github")
        self.assertEqual(ns.github_command, "install")
        self.assertEqual(ns.path, ".github/workflows/oa.yml")
        self.assertTrue(ns.force)

    def test_github_run_parses(self) -> None:
        from openagentic_cli.args import parse_args

        ns = parse_args(["github", "run", "--event-path", "event.json", "--print-prompt"])
        self.assertEqual(ns.command, "github")
        self.assertEqual(ns.github_command, "run")
        self.assertEqual(ns.event_path, "event.json")
        self.assertTrue(ns.print_prompt)


if __name__ == "__main__":
    unittest.main()
