import unittest


class TestLspConfigBuiltinOverride(unittest.TestCase):
    def test_builtin_id_does_not_require_extensions(self) -> None:
        """OpenCode parity: built-in LSP server ids don't require extensions in config."""

        from openagentic_sdk.lsp.config import parse_lsp_config

        cfg = {
            "lsp": {
                "pyright": {
                    "command": ["pyright-langserver", "--stdio"],
                }
            }
        }

        parsed = parse_lsp_config(cfg)
        self.assertTrue(parsed.enabled)
        ids = [s.server_id for s in parsed.servers]
        self.assertIn("pyright", ids)


if __name__ == "__main__":
    unittest.main()
