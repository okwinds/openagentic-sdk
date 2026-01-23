from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .base import Tool, ToolContext


SearchTransport = Callable[[str, Mapping[str, str], Mapping[str, Any]], Mapping[str, Any]]


def _default_search_transport(url: str, headers: Mapping[str, str], payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class WebSearchTool(Tool):
    name: str = "WebSearch"
    description: str = "Search the web (Tavily backend)."
    transport: SearchTransport = _default_search_transport
    endpoint: str = "https://api.tavily.com/search"

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        query = tool_input.get("query")
        if not isinstance(query, str) or not query:
            raise ValueError("WebSearch: 'query' must be a non-empty string")
        max_results = tool_input.get("max_results", 5)
        if not isinstance(max_results, int) or max_results <= 0:
            raise ValueError("WebSearch: 'max_results' must be a positive integer")

        allowed_domains = tool_input.get("allowed_domains")
        blocked_domains = tool_input.get("blocked_domains")
        if allowed_domains is not None and not isinstance(allowed_domains, list):
            raise ValueError("WebSearch: 'allowed_domains' must be a list of strings")
        if blocked_domains is not None and not isinstance(blocked_domains, list):
            raise ValueError("WebSearch: 'blocked_domains' must be a list of strings")
        allowed_set = {str(d).lower() for d in allowed_domains or []}
        blocked_set = {str(d).lower() for d in blocked_domains or []}

        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("WebSearch: missing TAVILY_API_KEY")

        headers = {"content-type": "application/json"}
        payload = {"api_key": api_key, "query": query, "max_results": max_results}
        obj = self.transport(self.endpoint, headers, payload)
        results_in = obj.get("results") if isinstance(obj, dict) else None

        results: list[dict[str, Any]] = []
        if isinstance(results_in, list):
            for r in results_in:
                if not isinstance(r, dict):
                    continue
                url = r.get("url")
                host = ""
                if isinstance(url, str):
                    try:
                        import urllib.parse

                        host = (urllib.parse.urlparse(url).hostname or "").lower()
                    except Exception:  # noqa: BLE001
                        host = ""
                if blocked_set and host and any(host == b or host.endswith("." + b) for b in blocked_set):
                    continue
                if allowed_set and host and not any(host == a or host.endswith("." + a) for a in allowed_set):
                    continue
                results.append(
                    {
                        "title": r.get("title"),
                        "url": url,
                        "content": r.get("content") or r.get("snippet"),
                        "source": "tavily",
                    }
                )
        return {"query": query, "results": results, "total_results": len(results)}
