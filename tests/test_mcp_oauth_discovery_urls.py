import unittest


class TestMcpOauthDiscoveryUrls(unittest.TestCase):
    def test_prm_url_insertion_and_root_fallback(self) -> None:
        from openagentic_sdk.mcp.oauth import protected_resource_metadata_urls

        # RFC9728 path insertion for a resource with path.
        urls = protected_resource_metadata_urls("https://example.com/mcp")
        self.assertIn("https://example.com/.well-known/oauth-protected-resource/mcp", urls)
        # Root fallback also present.
        self.assertIn("https://example.com/.well-known/oauth-protected-resource", urls)

    def test_as_metadata_url_insertion(self) -> None:
        from openagentic_sdk.mcp.oauth import authorization_server_metadata_urls

        urls = authorization_server_metadata_urls("https://auth.example.com/tenant1")
        self.assertIn("https://auth.example.com/.well-known/oauth-authorization-server/tenant1", urls)
        # OIDC fallbacks should also be probed.
        self.assertTrue(any("openid-configuration" in u for u in urls))


if __name__ == "__main__":
    unittest.main()
