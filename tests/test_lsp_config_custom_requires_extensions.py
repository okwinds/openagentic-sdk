import unittest


class TestLspConfigCustomRequiresExtensions(unittest.TestCase):
    def test_custom_server_without_extensions_is_rejected(self) -> None:
        """OpenCode parity: custom LSP servers must declare extensions."""

        from openagentic_sdk.lsp.config import parse_lsp_config

        cfg = {
            "lsp": {
                "custom-lsp": {
                    "command": ["/bin/true"],
                }
            }
        }

        with self.assertRaises(Exception):
            _ = parse_lsp_config(cfg)


if __name__ == "__main__":
    unittest.main()
