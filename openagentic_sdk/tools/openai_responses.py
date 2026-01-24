from __future__ import annotations

from typing import Any, Mapping, Sequence

from .openai import tool_schemas_for_openai
from .registry import ToolRegistry


def tool_schemas_for_responses(
    tool_names: Sequence[str],
    *,
    registry: ToolRegistry | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[Mapping[str, Any]]:
    schemas = tool_schemas_for_openai(tool_names, registry=registry, context=context)
    out: list[Mapping[str, Any]] = []
    for t in schemas:
        if not isinstance(t, dict):
            continue
        if t.get("type") != "function":
            continue
        fn = t.get("function")
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not isinstance(name, str) or not name:
            continue
        tool: dict[str, Any] = {"type": "function", "name": name}
        desc = fn.get("description")
        if isinstance(desc, str) and desc:
            tool["description"] = desc
        params = fn.get("parameters")
        tool["parameters"] = params if isinstance(params, dict) else {"type": "object", "properties": {}}
        out.append(tool)
    return out

