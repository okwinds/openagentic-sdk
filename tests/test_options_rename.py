import unittest


class TestOptionsRename(unittest.TestCase):
    def test_openagenticoptions_is_exported(self) -> None:
        import openagentic_sdk

        self.assertTrue(hasattr(openagentic_sdk, "OpenAgenticOptions"))
        self.assertFalse(hasattr(openagentic_sdk, "OpenAgentOptions"))

        from openagentic_sdk.options import OpenAgenticOptions  # noqa: F401


if __name__ == "__main__":
    unittest.main()
