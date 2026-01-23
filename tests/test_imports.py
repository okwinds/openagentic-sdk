import unittest


class TestImports(unittest.TestCase):
    def test_import_open_agent_sdk(self) -> None:
        import open_agent_sdk  # noqa: F401


if __name__ == "__main__":
    unittest.main()

