import unittest


class TestInstallImport(unittest.TestCase):
    def test_import_open_agent_sdk(self) -> None:
        import openagentic_sdk  # noqa: F401


if __name__ == "__main__":
    unittest.main()

