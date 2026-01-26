from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .base import Tool, ToolContext

FetchTransport = Callable[[str, Mapping[str, str]], tuple[int, Mapping[str, str], bytes]]

_getaddrinfo = socket.getaddrinfo


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Prevent urllib from transparently following redirects. We need to enforce
    # host allow/deny checks on every hop.
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        _ = (req, fp, code, msg, headers, newurl)
        return None


def _default_fetch_transport(url: str, headers: Mapping[str, str]) -> tuple[int, Mapping[str, str], bytes]:
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60) as resp:
            status = int(getattr(resp, "status", 200))
            resp_headers = {k.lower(): v for k, v in dict(resp.headers).items()}
            body = resp.read()
    except urllib.error.HTTPError as e:
        # urllib raises for 3xx when redirects are disabled; treat as a response.
        status = int(getattr(e, "code", 0) or 0)
        resp_headers = {k.lower(): v for k, v in dict(getattr(e, "headers", {}) or {}).items()}
        try:
            body = e.read()  # type: ignore[assignment]
        except Exception:  # noqa: BLE001
            body = b""
    return status, resp_headers, body


def _is_blocked_host(host: str) -> bool:
    host_lower = host.lower()
    if host_lower in ("localhost",):
        return True
    if host_lower.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            infos = _getaddrinfo(host, 0)
        except Exception:  # noqa: BLE001
            return False
        for _family, _socktype, _proto, _canonname, sockaddr in infos:
            ip_str = None
            if isinstance(sockaddr, tuple) and sockaddr:
                ip_str = sockaddr[0]
            if not isinstance(ip_str, str) or not ip_str:
                continue
            try:
                ip2 = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if ip2.is_private or ip2.is_loopback or ip2.is_link_local:
                return True
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


@dataclass(frozen=True, slots=True)
class WebFetchTool(Tool):
    name: str = "WebFetch"
    description: str = "Fetch a URL over HTTP(S)."
    max_bytes: int = 1024 * 1024
    max_redirects: int = 5
    allow_private_networks: bool = False
    transport: FetchTransport = _default_fetch_transport

    def _validate_url(self, url: str) -> urllib.parse.ParseResult:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("WebFetch: only http/https URLs are allowed")
        if not parsed.hostname:
            raise ValueError("WebFetch: URL must include a hostname")
        if not self.allow_private_networks and _is_blocked_host(parsed.hostname):
            raise ValueError("WebFetch: blocked hostname")
        return parsed

    def _coerce_headers(self, headers: Mapping[str, Any]) -> dict[str, str]:
        return {str(k).lower(): str(v) for k, v in headers.items()}

    def _next_url_from_location(self, *, current_url: str, location: str) -> str:
        # Location can be relative; join against the current URL.
        return urllib.parse.urljoin(current_url, location)

    def _fetch_following_redirects(
        self, *, url: str, headers: Mapping[str, str]
    ) -> tuple[str, int, Mapping[str, str], bytes, list[str]]:
        chain: list[str] = [url]
        current_url = url
        for _ in range(max(0, int(self.max_redirects)) + 1):
            status, resp_headers_raw, body = self.transport(current_url, headers)
            resp_headers = {str(k).lower(): str(v) for k, v in (resp_headers_raw or {}).items()}

            if status in (301, 302, 303, 307, 308):
                loc = resp_headers.get("location")
                if not loc:
                    return current_url, status, resp_headers, body, chain
                next_url = self._next_url_from_location(current_url=current_url, location=loc)
                self._validate_url(next_url)
                current_url = next_url
                chain.append(current_url)
                continue

            return current_url, status, resp_headers, body, chain

        raise ValueError(f"WebFetch: too many redirects (>{self.max_redirects})")

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        url = tool_input.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("WebFetch: 'url' must be a non-empty string")
        requested_url = url
        self._validate_url(requested_url)

        headers = tool_input.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError("WebFetch: 'headers' must be an object")

        final_url, status, resp_headers, body, redirect_chain = self._fetch_following_redirects(
            url=requested_url, headers=self._coerce_headers(headers)
        )
        if len(body) > self.max_bytes:
            body = body[: self.max_bytes]

        content_type = resp_headers.get("content-type")
        text = body.decode("utf-8", errors="replace")
        return {
            # Keep compatibility while making the final URL explicit.
            "requested_url": requested_url,
            "url": final_url,
            "final_url": final_url,
            "redirect_chain": list(redirect_chain),
            "status": status,
            "content_type": content_type,
            "text": text,
        }
