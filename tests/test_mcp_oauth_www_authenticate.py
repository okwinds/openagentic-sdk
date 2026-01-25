import unittest


class TestMcpOauthWwwAuthenticate(unittest.TestCase):
    def test_parses_bearer_resource_metadata_and_scope(self) -> None:
        from openagentic_sdk.mcp.oauth import parse_www_authenticate

        header = 'Bearer realm="mcp", resource_metadata="https://srv/.well-known/oauth-protected-resource", scope="mcp:tools"'
        parsed = parse_www_authenticate(header)
        self.assertEqual(parsed.get("scheme"), "bearer")
        params = parsed.get("params")
        self.assertIsInstance(params, dict)
        self.assertEqual(params.get("resource_metadata"), "https://srv/.well-known/oauth-protected-resource")
        self.assertEqual(params.get("scope"), "mcp:tools")

    def test_parses_insufficient_scope_error(self) -> None:
        from openagentic_sdk.mcp.oauth import parse_www_authenticate

        header = 'Bearer error="insufficient_scope", scope="mcp:resources"'
        parsed = parse_www_authenticate(header)
        params = parsed.get("params")
        self.assertEqual(params.get("error"), "insufficient_scope")
        self.assertEqual(params.get("scope"), "mcp:resources")


if __name__ == "__main__":
    unittest.main()
