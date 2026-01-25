from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

import asyncio
import webbrowser

from openagentic_sdk.mcp.credentials import McpCredentialStore
from openagentic_sdk.mcp.auth_store import McpAuthStore
from openagentic_sdk.mcp.oauth_flow import McpOAuthManager, OpenUrl
from openagentic_sdk.opencode_config import load_merged_config


@dataclass(frozen=True, slots=True)
class McpListItem:
    name: str
    type: str
    url: str | None = None


def list_configured_mcp_servers(*, cwd: str) -> list[McpListItem]:
    cfg = load_merged_config(cwd=cwd)
    mcp = cfg.get("mcp") if isinstance(cfg, dict) else None
    if not isinstance(mcp, dict):
        return []
    out: list[McpListItem] = []
    for k, v in mcp.items():
        if not isinstance(k, str) or not k:
            continue
        if not isinstance(v, dict):
            continue
        typ = v.get("type")
        if typ == "remote":
            url = v.get("url")
            out.append(McpListItem(name=k, type="remote", url=str(url) if isinstance(url, str) else None))
        elif typ == "local":
            out.append(McpListItem(name=k, type="local", url=None))
    return out


def cmd_mcp_list(*, cwd: str) -> str:
    items = list_configured_mcp_servers(cwd=cwd)
    if not items:
        return "No MCP servers configured in opencode.json/.opencode/opencode.json."
    lines: list[str] = []
    for it in items:
        if it.type == "remote":
            lines.append(f"- {it.name}: remote {it.url or ''}".rstrip())
        else:
            lines.append(f"- {it.name}: local")
    return "\n".join(lines)


def cmd_mcp_auth(
    *,
    cwd: str,
    name: str,
    token: str | None,
    open_url: OpenUrl | None = None,
    callback_port: int = 19876,
) -> str:
    # 1) Manual bearer-token flow (legacy / non-OAuth).
    if isinstance(token, str) and token.strip():
        store = McpCredentialStore.load_default()
        store.set_bearer_token(name, token.strip())
        store.save()
        return f"Stored MCP bearer token for {name}."

    # 2) OAuth flow (OpenCode parity): discover from config + run auth-code flow.
    cfg = load_merged_config(cwd=cwd)
    mcp = cfg.get("mcp") if isinstance(cfg, dict) else None
    if not isinstance(mcp, dict) or name not in mcp:
        return f"MCP server not found in config: {name}"
    spec = mcp.get(name)
    if not isinstance(spec, dict) or spec.get("type") != "remote":
        return f"MCP server {name} is not a remote server"
    url = spec.get("url")
    if not isinstance(url, str) or not url:
        return f"MCP server {name} is missing url"
    oauth = spec.get("oauth")
    if oauth is False:
        return f"MCP server {name} has oauth disabled"
    scope = None
    if isinstance(oauth, dict):
        s = oauth.get("scope")
        if isinstance(s, str) and s.strip():
            scope = s.strip()

    if open_url is None:
        async def _open(u: str) -> None:
            # webbrowser.open() is blocking-ish and OS-dependent; run in a thread.
            await asyncio.to_thread(webbrowser.open, u)

        open_url = _open

    mgr = McpOAuthManager(callback_port=int(callback_port) if callback_port else 19876)
    _ = asyncio.run(mgr.authenticate(server_key=name, server_url=url, scope=scope, open_url=open_url))
    return f"OAuth complete for {name}. Token stored."


def cmd_mcp_logout(*, name: str) -> str:
    store = McpCredentialStore.load_default()
    store.clear(name)
    store.save()
    # Also clear OAuth credentials.
    auth = McpAuthStore.load_default()
    auth.remove(name)
    auth.save()
    return f"Cleared MCP credentials for {name}."
