from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Generic, Literal, Mapping, TypeVar

from ..tools.base import Tool, ToolContext

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SdkMcpTool(Generic[T]):
    name: str
    description: str
    input_schema: type[T] | dict[str, Any]
    handler: Callable[[Any], Awaitable[dict[str, Any]]]


def tool(
    name: str,
    description: str,
    input_schema: type | dict[str, Any],
) -> Callable[[Callable[[Any], Awaitable[dict[str, Any]]]], SdkMcpTool[Any]]:
    def decorator(fn: Callable[[Any], Awaitable[dict[str, Any]]]) -> SdkMcpTool[Any]:
        return SdkMcpTool(name=name, description=description, input_schema=input_schema, handler=fn)

    return decorator


def _schema_from_type_map(type_map: Mapping[str, Any]) -> dict[str, Any]:
    def _t(t: Any) -> dict[str, Any]:
        if t is str:
            return {"type": "string"}
        if t is int:
            return {"type": "integer"}
        if t is float:
            return {"type": "number"}
        if t is bool:
            return {"type": "boolean"}
        return {"type": "string"}

    props: dict[str, Any] = {}
    required: list[str] = []
    for k, v in type_map.items():
        props[str(k)] = _t(v)
        required.append(str(k))
    return {"type": "object", "properties": props, "required": required}


def tool_schema_for_openai(tool_name: str, description: str, input_schema: type | dict[str, Any]) -> dict[str, Any]:
    parameters: dict[str, Any]
    if isinstance(input_schema, dict):
        # Either type-map {"x": str} or raw JSON schema. Detect by "type".
        if input_schema.get("type") == "object" or "properties" in input_schema:
            parameters = dict(input_schema)
        else:
            parameters = _schema_from_type_map(input_schema)
    else:
        # Minimal: no validation, accept any object.
        parameters = {"type": "object"}
    return {
        "type": "function",
        "function": {"name": tool_name, "description": description, "parameters": parameters},
    }


@dataclass(frozen=True, slots=True)
class McpSdkServerConfig:
    type: Literal["sdk"] = "sdk"
    name: str = ""
    version: str = "1.0.0"
    tools: list[SdkMcpTool[Any]] = field(default_factory=list)


def create_sdk_mcp_server(
    name: str,
    version: str = "1.0.0",
    tools: list[SdkMcpTool[Any]] | None = None,
) -> McpSdkServerConfig:
    return McpSdkServerConfig(name=name, version=version, tools=list(tools or []))


@dataclass(frozen=True, slots=True)
class McpSdkToolWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _tool: SdkMcpTool[Any]

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        _ = ctx
        return await self._tool.handler(dict(tool_input))


def wrap_sdk_server_tools(server_key: str, server: McpSdkServerConfig) -> list[McpSdkToolWrapper]:
    wrappers: list[McpSdkToolWrapper] = []
    for t in server.tools:
        full_name = f"mcp__{server_key}__{t.name}"
        wrappers.append(
            McpSdkToolWrapper(
                name=full_name,
                description=t.description,
                openai_schema=tool_schema_for_openai(full_name, t.description, t.input_schema),
                _tool=t,
            )
        )
    return wrappers
