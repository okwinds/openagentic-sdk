from __future__ import annotations

import asyncio
import base64
import hashlib
import http.client
import io
import json
import os
import time
import urllib.error
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

from .auth_store import McpAuthStore, McpClientInfo, McpTokens
from .oauth import authorization_server_metadata_urls, protected_resource_metadata_urls
from .oauth_callback import OAuthCallbackServer

from urllib.parse import urlparse


OpenUrl = Callable[[str], Awaitable[None]]


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _pkce_verifier() -> str:
    # 32 bytes is a reasonable minimum; encoded as URL-safe base64.
    return _b64url_no_pad(os.urandom(32))


def _pkce_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64url_no_pad(digest)


def _oauth_state() -> str:
    # Match OpenCode style: 32 random bytes hex.
    return os.urandom(32).hex()


def _scope_includes(stored: str | None, required: str | None) -> bool:
    if not required:
        return True
    req = {s for s in str(required).split() if s}
    if not req:
        return True
    st = {s for s in str(stored or "").split() if s}
    return req.issubset(st)


def _http_get_json(url: str, *, timeout_s: float = 5.0) -> Mapping[str, Any]:
    raw = _http_request_raw(
        url,
        method="GET",
        headers={"Accept": "application/json"},
        timeout_s=timeout_s,
        allow_redirects=True,
    )
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def _http_post_json(url: str, payload: Mapping[str, Any], *, timeout_s: float = 10.0) -> Mapping[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    raw = _http_request_raw(
        url,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        body=data,
        timeout_s=timeout_s,
        allow_redirects=False,
    )
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def _http_post_form(url: str, params: Mapping[str, str], *, timeout_s: float = 10.0) -> Mapping[str, Any]:
    body = urllib.parse.urlencode(dict(params)).encode("utf-8")
    raw = _http_request_raw(
        url,
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        body=body,
        timeout_s=timeout_s,
        allow_redirects=False,
    )
    obj = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj


def _http_request_raw(
    url: str,
    *,
    method: str,
    headers: Mapping[str, str],
    body: bytes | None = None,
    timeout_s: float,
    allow_redirects: bool,
    max_redirects: int = 5,
) -> bytes:
    current_url = url
    redirects_left = max_redirects

    while True:
        parts = urllib.parse.urlsplit(current_url)
        if parts.scheme not in ("http", "https"):
            raise ValueError(f"unsupported URL scheme: {parts.scheme}")
        if not parts.hostname:
            raise ValueError("URL missing hostname")

        port = parts.port or (443 if parts.scheme == "https" else 80)
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query

        conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(parts.hostname, port, timeout=float(timeout_s))
        try:
            conn.request(method, target, body=body, headers=dict(headers))
            resp = conn.getresponse()
            raw = resp.read()

            if allow_redirects and method == "GET" and resp.status in (301, 302, 303, 307, 308):
                loc = resp.getheader("Location")
                if not loc:
                    raise urllib.error.HTTPError(current_url, resp.status, resp.reason, resp.headers, io.BytesIO(raw))
                if redirects_left <= 0:
                    raise RuntimeError(f"too many redirects while fetching {url!r}")
                current_url = urllib.parse.urljoin(current_url, loc)
                redirects_left -= 1
                continue

            if resp.status >= 400:
                raise urllib.error.HTTPError(current_url, resp.status, resp.reason, resp.headers, io.BytesIO(raw))

            return raw
        finally:
            conn.close()


def _first_json(urls: list[str], *, timeout_s: float = 5.0) -> Mapping[str, Any]:
    last: Exception | None = None
    for u in urls:
        try:
            return _http_get_json(u, timeout_s=timeout_s)
        except Exception as e:  # noqa: BLE001
            last = e
            continue
    raise RuntimeError(f"failed to fetch metadata from any URL: {urls!r}; last={last!r}")


@dataclass
class McpOAuthManager:
    """MCP OAuth manager (authorization-code + PKCE + DCR).

    This is intentionally standalone (stdlib HTTP + local callback server) so it
    can run without extra dependencies.
    """

    home: str | None = None
    callback_port: int = 19876

    def __post_init__(self) -> None:
        base = Path(self.home).expanduser() if self.home else None
        if base is None:
            self.auth_store = McpAuthStore.load_default()
        else:
            self.auth_store = McpAuthStore.load(base / "mcp" / "mcp-auth.json")

    async def authenticate(
        self,
        *,
        server_key: str,
        server_url: str,
        scope: str | None,
        open_url: OpenUrl,
        timeout_s: float = 300.0,
    ) -> str:
        u = urlparse(str(server_url or ""))
        if u.scheme not in ("http", "https"):
            raise ValueError(f"unsupported server_url scheme: {u.scheme}")
        if not u.netloc:
            raise ValueError("server_url missing hostname")

        # Fast-path: existing token for this URL.
        entry = self.auth_store.get_for_url(server_key, server_url=server_url)
        if entry is not None and entry.tokens is not None:
            expired = self.auth_store.is_token_expired(server_key)
            # If the server is asking for a broader scope than we have, force
            # a step-up reauth.
            if expired is False and entry.tokens.access_token and _scope_includes(entry.tokens.scope, scope):
                return entry.tokens.access_token

            # Refresh path: avoid opening a browser if we can refresh silently.
            if expired is True and entry.tokens.refresh_token and entry.client_info is not None:
                try:
                    access = await self._refresh(
                        server_key=server_key,
                        server_url=server_url,
                        refresh_token=entry.tokens.refresh_token,
                        client=entry.client_info,
                        scope=scope,
                    )
                    if access:
                        return access
                except Exception:
                    # Fall back to interactive auth code flow.
                    pass

        # Discover PRM -> issuer -> AS metadata.
        prm = await asyncio.to_thread(_first_json, protected_resource_metadata_urls(server_url))
        issuers = prm.get("authorization_servers")
        if not isinstance(issuers, list) or not issuers or not isinstance(issuers[0], str):
            raise RuntimeError("PRM missing authorization_servers")
        issuer = issuers[0]
        meta = await asyncio.to_thread(_first_json, authorization_server_metadata_urls(issuer))
        auth_ep = meta.get("authorization_endpoint")
        token_ep = meta.get("token_endpoint")
        reg_ep = meta.get("registration_endpoint")
        if not isinstance(auth_ep, str) or not isinstance(token_ep, str):
            raise RuntimeError("auth server metadata missing endpoints")

        # Ensure we have a client.
        entry = self.auth_store.get_for_url(server_key, server_url=server_url)
        client = entry.client_info if entry is not None else None
        if client is None:
            if not isinstance(reg_ep, str) or not reg_ep:
                raise RuntimeError("no client configured and no registration_endpoint")

            callback = OAuthCallbackServer(host="127.0.0.1", port=int(self.callback_port))
            await callback.start()
            try:
                reg = await asyncio.to_thread(
                    _http_post_json,
                    reg_ep,
                    {
                        "client_name": "openagentic-sdk",
                        "redirect_uris": [callback.redirect_uri],
                        "grant_types": ["authorization_code", "refresh_token"],
                        "response_types": ["code"],
                    },
                )
            finally:
                await callback.close()

            cid = reg.get("client_id")
            if not isinstance(cid, str) or not cid:
                raise RuntimeError("dynamic registration missing client_id")
            cs = reg.get("client_secret") if isinstance(reg.get("client_secret"), str) else None
            cse = reg.get("client_secret_expires_at")
            cse2 = float(cse) if isinstance(cse, (int, float)) else None
            client = McpClientInfo(client_id=cid, client_secret=cs, client_secret_expires_at=cse2)
            self.auth_store.update_client_info(server_key, client, server_url=server_url)
            self.auth_store.save()

        # Full auth code flow.
        callback = OAuthCallbackServer(host="127.0.0.1", port=int(self.callback_port))
        await callback.start()
        try:
            state = _oauth_state()
            verifier = _pkce_verifier()
            challenge = _pkce_challenge_s256(verifier)
            self.auth_store.update_oauth_state(server_key, state)
            self.auth_store.update_code_verifier(server_key, verifier)
            self.auth_store.save()

            params: dict[str, str] = {
                "response_type": "code",
                "client_id": client.client_id,
                "redirect_uri": callback.redirect_uri,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "resource": server_url,
            }
            if scope:
                params["scope"] = scope
            auth_url = auth_ep + ("&" if "?" in auth_ep else "?") + urllib.parse.urlencode(params)

            # Register waiter before opening URL to avoid races.
            waiter = asyncio.create_task(callback.wait_for_callback(state, timeout_s=timeout_s))
            await asyncio.sleep(0)
            await open_url(auth_url)
            code = await waiter

            # Token exchange.
            token_params: dict[str, str] = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback.redirect_uri,
                "client_id": client.client_id,
                "code_verifier": verifier,
                "resource": server_url,
            }
            if client.client_secret:
                token_params["client_secret"] = client.client_secret
            tok = await asyncio.to_thread(_http_post_form, token_ep, token_params)

            access = tok.get("access_token")
            if not isinstance(access, str) or not access:
                raise RuntimeError("token response missing access_token")
            refresh = tok.get("refresh_token") if isinstance(tok.get("refresh_token"), str) else None
            expires_in = tok.get("expires_in")
            expires_at = time.time() + float(expires_in) if isinstance(expires_in, (int, float)) else None
            scope2 = tok.get("scope") if isinstance(tok.get("scope"), str) else None

            self.auth_store.update_tokens(
                server_key,
                McpTokens(access_token=access, refresh_token=refresh, expires_at=expires_at, scope=scope2),
                server_url=server_url,
            )
            self.auth_store.clear_code_verifier(server_key)
            self.auth_store.clear_oauth_state(server_key)
            self.auth_store.save()
            return access
        finally:
            await callback.close()

    async def _refresh(
        self,
        *,
        server_key: str,
        server_url: str,
        refresh_token: str,
        client: McpClientInfo,
        scope: str | None,
    ) -> str | None:
        prm = await asyncio.to_thread(_first_json, protected_resource_metadata_urls(server_url))
        issuers = prm.get("authorization_servers")
        if not isinstance(issuers, list) or not issuers or not isinstance(issuers[0], str):
            return None
        issuer = issuers[0]
        meta = await asyncio.to_thread(_first_json, authorization_server_metadata_urls(issuer))
        token_ep = meta.get("token_endpoint")
        if not isinstance(token_ep, str) or not token_ep:
            return None

        params: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client.client_id,
            "resource": server_url,
        }
        if client.client_secret:
            params["client_secret"] = client.client_secret
        if scope:
            params["scope"] = scope

        tok = await asyncio.to_thread(_http_post_form, token_ep, params)
        access = tok.get("access_token")
        if not isinstance(access, str) or not access:
            return None
        refresh2 = tok.get("refresh_token") if isinstance(tok.get("refresh_token"), str) else refresh_token
        expires_in = tok.get("expires_in")
        expires_at = time.time() + float(expires_in) if isinstance(expires_in, (int, float)) else None
        scope2 = tok.get("scope") if isinstance(tok.get("scope"), str) else None

        self.auth_store.update_tokens(
            server_key,
            McpTokens(access_token=access, refresh_token=refresh2, expires_at=expires_at, scope=scope2),
            server_url=server_url,
        )
        self.auth_store.save()
        return access
