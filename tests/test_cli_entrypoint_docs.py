import unittest


class TestCliEntrypointDocs(unittest.TestCase):
    def test_cli_main_exists(self) -> None:
        from openagentic_cli.__main__ import main

        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()

