from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..lsp import LspManager, parse_lsp_config
from ..opencode_config import load_merged_config
from .base import Tool, ToolContext


_DESCRIPTION = """Interact with Language Server Protocol (LSP) servers to get code intelligence features.

Supported operations:
- goToDefinition: Find where a symbol is defined
- findReferences: Find all references to a symbol
- hover: Get hover information (documentation, type info) for a symbol
- documentSymbol: Get all symbols (functions, classes, variables) in a document
- workspaceSymbol: Search for symbols across the entire workspace
- goToImplementation: Find implementations of an interface or abstract method
- prepareCallHierarchy: Get call hierarchy item at a position (functions/methods)
- incomingCalls: Find all functions/methods that call the function at a position
- outgoingCalls: Find all functions/methods called by the function at a position

All operations require:
- filePath: The absolute or relative path to the file
- line: The line number (1-based)
- character: The character offset (1-based)

Note: LSP servers must be configured for the file type via OpenCode-style config (opencode.json / .opencode/opencode.json).
""".strip()


@dataclass(frozen=True, slots=True)
class LspTool(Tool):
    name: str = "lsp"
    description: str = _DESCRIPTION

    openai_schema: dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.openai_schema is None:
            object.__setattr__(
                self,
                "openai_schema",
                {
                    "type": "function",
                    "function": {
                        "name": "lsp",
                        "description": self.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "enum": [
                                        "goToDefinition",
                                        "findReferences",
                                        "hover",
                                        "documentSymbol",
                                        "workspaceSymbol",
                                        "goToImplementation",
                                        "prepareCallHierarchy",
                                        "incomingCalls",
                                        "outgoingCalls",
                                    ],
                                },
                                "filePath": {"type": "string"},
                                "file_path": {"type": "string"},
                                "line": {"type": "integer", "minimum": 1},
                                "character": {"type": "integer", "minimum": 1},
                            },
                            "required": ["operation", "filePath", "line", "character"],
                        },
                    },
                },
            )

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        op = tool_input.get("operation")
        if not isinstance(op, str) or not op:
            raise ValueError("lsp: 'operation' must be a non-empty string")

        file_path = tool_input.get("filePath", tool_input.get("file_path"))
        if not isinstance(file_path, str) or not file_path:
            raise ValueError("lsp: 'filePath' must be a non-empty string")

        p = Path(file_path)
        if not p.is_absolute():
            p = Path(ctx.cwd) / p
        p = p.resolve()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")

        line = tool_input.get("line")
        character = tool_input.get("character")
        if not isinstance(line, int) or line < 1:
            raise ValueError("lsp: 'line' must be an integer >= 1")
        if not isinstance(character, int) or character < 1:
            raise ValueError("lsp: 'character' must be an integer >= 1")

        root = ctx.project_dir or ctx.cwd
        cfg = load_merged_config(cwd=str(root))
        lsp_cfg = parse_lsp_config(cfg)
        if not lsp_cfg.enabled:
            raise RuntimeError("lsp: disabled by config")

        async with LspManager(config=lsp_cfg, project_root=str(root)) as mgr:
            res = await mgr.op(operation=op, file_path=str(p), line0=line - 1, character0=character - 1)

        # Normalize output to OpenCode-like shape for agent consumption.
        title = f"{op} {p}:{line}:{character}"
        # OpenCode returns arrays for most ops; keep whatever the server returns.
        result_obj = res
        empty = result_obj is None or (isinstance(result_obj, list) and not result_obj)
        output = f"No results found for {op}" if empty else _safe_pretty_json(result_obj)
        return {"title": title, "metadata": {"result": result_obj}, "output": output}


def _safe_pretty_json(obj: Any) -> str:
    import json

    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return str(obj)
