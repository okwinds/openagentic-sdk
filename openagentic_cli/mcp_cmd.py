from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openagentic_sdk.mcp.credentials import McpCredentialStore
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


def cmd_mcp_auth(*, name: str, token: str) -> str:
    store = McpCredentialStore.load_default()
    store.set_bearer_token(name, token)
    store.save()
    return f"Stored MCP bearer token for {name}."


def cmd_mcp_logout(*, name: str) -> str:
    store = McpCredentialStore.load_default()
    store.clear(name)
    store.save()
    return f"Cleared MCP credentials for {name}."
