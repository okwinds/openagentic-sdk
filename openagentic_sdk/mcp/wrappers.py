from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from ..tools.base import Tool, ToolContext
from .client import StdioMcpClient


class _RemoteMcpClient(Protocol):
    async def call_tool(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def list_tools(self) -> list[dict[str, Any]]:
        ...

    async def list_prompts(self) -> list[dict[str, Any]]:
        ...

    async def get_prompt(self, *, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        ...

    async def list_resources(self) -> list[dict[str, Any]]:
        ...

    async def read_resource(self, *, uri: str) -> dict[str, Any]:
        ...


def _openai_schema_for_mcp_tool(full_name: str, description: str, input_schema: Any) -> dict[str, Any]:
    parameters: dict[str, Any]
    if isinstance(input_schema, dict):
        parameters = dict(input_schema)
        if parameters.get("type") != "object":
            parameters = {"type": "object"}
    else:
        parameters = {"type": "object"}
    return {
        "type": "function",
        "function": {"name": full_name, "description": description, "parameters": parameters},
    }


@dataclass(frozen=True, slots=True)
class McpStdioToolWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _client: StdioMcpClient
    _tool_name: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        res = await self._client.call_tool(name=self._tool_name, arguments=dict(tool_input))
        # Stable, minimal surface: expose text plus raw result.
        return {"text": res.get("text", ""), "content": res.get("content"), "raw": res.get("raw")}


def wrap_stdio_mcp_tools(server_key: str, *, client: StdioMcpClient, tools: list[dict[str, Any]]) -> list[McpStdioToolWrapper]:
    out: list[McpStdioToolWrapper] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name:
            continue
        desc = t.get("description") if isinstance(t.get("description"), str) else ""
        schema = t.get("inputSchema") if isinstance(t.get("inputSchema"), dict) else {"type": "object"}
        full = f"mcp__{server_key}__{name}"
        out.append(
            McpStdioToolWrapper(
                name=full,
                description=desc or f"MCP tool {name}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP tool {name}", schema),
                _client=client,
                _tool_name=name,
            )
        )
    return out


def wrap_stdio_mcp_prompts(server_key: str, *, client: StdioMcpClient, prompts: list[dict[str, Any]]) -> list[Tool]:
    # OpenCode exposes prompts as first-class commands; in this SDK we wrap
    # them as tools (and later layer command-parity on top).
    out: list[Tool] = []
    for p in prompts:
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        if not isinstance(name, str) or not name:
            continue
        desc = p.get("description") if isinstance(p.get("description"), str) else ""
        full = f"mcp__{server_key}__prompt__{name}"
        out.append(
            McpHttpPromptWrapper(
                name=full,
                description=desc or f"MCP prompt {name}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP prompt {name}", {"type": "object"}),
                _client=client,  # type: ignore[arg-type]
                _prompt_name=name,
            )
        )
    return out


def wrap_stdio_mcp_resources(server_key: str, *, client: StdioMcpClient, resources: list[dict[str, Any]]) -> list[Tool]:
    out: list[Tool] = []
    for r in resources:
        if not isinstance(r, dict):
            continue
        uri = r.get("uri") or r.get("name")
        if not isinstance(uri, str) or not uri:
            continue
        desc = r.get("description") if isinstance(r.get("description"), str) else ""
        safe_name = uri.replace(":", "_").replace("/", "_")
        full = f"mcp__{server_key}__resource__{safe_name}"
        out.append(
            McpHttpResourceWrapper(
                name=full,
                description=desc or f"MCP resource {uri}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP resource {uri}", {"type": "object"}),
                _client=client,  # type: ignore[arg-type]
                _uri=uri,
            )
        )
    return out


@dataclass(frozen=True, slots=True)
class McpHttpToolWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _client: _RemoteMcpClient
    _tool_name: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        res = await self._client.call_tool(name=self._tool_name, arguments=dict(tool_input))
        return {"text": res.get("text", ""), "content": res.get("content"), "raw": res.get("raw")}


def wrap_http_mcp_tools(server_key: str, *, client: _RemoteMcpClient, tools: list[dict[str, Any]]) -> list[McpHttpToolWrapper]:
    out: list[McpHttpToolWrapper] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name:
            continue
        desc = t.get("description") if isinstance(t.get("description"), str) else ""
        schema = t.get("inputSchema") if isinstance(t.get("inputSchema"), dict) else {"type": "object"}
        full = f"mcp__{server_key}__{name}"
        out.append(
            McpHttpToolWrapper(
                name=full,
                description=desc or f"MCP tool {name}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP tool {name}", schema),
                _client=client,
                _tool_name=name,
            )
        )
    return out


@dataclass(frozen=True, slots=True)
class McpHttpPromptWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _client: _RemoteMcpClient
    _prompt_name: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        res = await self._client.get_prompt(name=self._prompt_name, arguments=dict(tool_input))
        return {"text": res.get("text", ""), "content": res.get("content"), "raw": res.get("raw")}


def wrap_http_mcp_prompts(server_key: str, *, client: _RemoteMcpClient, prompts: list[dict[str, Any]]) -> list[McpHttpPromptWrapper]:
    out: list[McpHttpPromptWrapper] = []
    for p in prompts:
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        if not isinstance(name, str) or not name:
            continue
        desc = p.get("description") if isinstance(p.get("description"), str) else ""
        full = f"mcp__{server_key}__prompt__{name}"
        out.append(
            McpHttpPromptWrapper(
                name=full,
                description=desc or f"MCP prompt {name}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP prompt {name}", {"type": "object"}),
                _client=client,
                _prompt_name=name,
            )
        )
    return out


@dataclass(frozen=True, slots=True)
class McpHttpResourceWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _client: _RemoteMcpClient
    _uri: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = (tool_input, ctx)
        res = await self._client.read_resource(uri=self._uri)
        return {"text": res.get("text", ""), "content": res.get("content"), "raw": res.get("raw")}


def wrap_http_mcp_resources(server_key: str, *, client: _RemoteMcpClient, resources: list[dict[str, Any]]) -> list[McpHttpResourceWrapper]:
    out: list[McpHttpResourceWrapper] = []
    for r in resources:
        if not isinstance(r, dict):
            continue
        uri = r.get("uri") or r.get("name")
        if not isinstance(uri, str) or not uri:
            continue
        desc = r.get("description") if isinstance(r.get("description"), str) else ""
        safe_name = uri.replace(":", "_").replace("/", "_")
        full = f"mcp__{server_key}__resource__{safe_name}"
        out.append(
            McpHttpResourceWrapper(
                name=full,
                description=desc or f"MCP resource {uri}",
                openai_schema=_openai_schema_for_mcp_tool(full, desc or f"MCP resource {uri}", {"type": "object"}),
                _client=client,
                _uri=uri,
            )
        )
    return out
