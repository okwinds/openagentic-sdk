import unittest


class TestCliImports(unittest.TestCase):
    def test_can_import_main(self) -> None:
        import open_agent_cli.__main__  # noqa: F401


if __name__ == "__main__":
    unittest.main()

