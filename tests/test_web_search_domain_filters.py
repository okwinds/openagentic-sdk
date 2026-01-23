import os
import unittest

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.web_search_tavily import WebSearchTool


class TestWebSearchDomainFilters(unittest.TestCase):
    def test_allowed_domains_filters_results(self) -> None:
        os.environ["TAVILY_API_KEY"] = "test"

        def transport(url, headers, payload):
            _ = (url, headers, payload)
            return {
                "results": [
                    {"title": "a", "url": "https://example.com/a", "content": "x"},
                    {"title": "b", "url": "https://other.com/b", "content": "y"},
                ]
            }

        tool = WebSearchTool(transport=transport)
        out = tool.run_sync(
            {"query": "x", "max_results": 5, "allowed_domains": ["example.com"]},
            ToolContext(cwd="/"),
        )
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["url"], "https://example.com/a")

    def test_blocked_domains_filters_results(self) -> None:
        os.environ["TAVILY_API_KEY"] = "test"

        def transport(url, headers, payload):
            _ = (url, headers, payload)
            return {
                "results": [
                    {"title": "a", "url": "https://example.com/a", "content": "x"},
                    {"title": "b", "url": "https://blocked.com/b", "content": "y"},
                ]
            }

        tool = WebSearchTool(transport=transport)
        out = tool.run_sync(
            {"query": "x", "max_results": 5, "blocked_domains": ["blocked.com"]},
            ToolContext(cwd="/"),
        )
        self.assertEqual(len(out["results"]), 1)
        self.assertEqual(out["results"][0]["url"], "https://example.com/a")


if __name__ == "__main__":
    unittest.main()

