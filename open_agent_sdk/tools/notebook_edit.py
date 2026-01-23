from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


def _normalize_source(new_source: str) -> list[str]:
    # Jupyter allows source as list[str] or str. Store list[str] for stability.
    if not new_source:
        return [""]
    if "\n" in new_source:
        return [ln + "\n" for ln in new_source.splitlines()]
    return [new_source]


@dataclass(frozen=True, slots=True)
class NotebookEditTool(Tool):
    name: str = "NotebookEdit"
    description: str = "Edit a Jupyter notebook (.ipynb)."

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        notebook_path = tool_input.get("notebook_path")
        if not isinstance(notebook_path, str) or not notebook_path:
            raise ValueError("NotebookEdit: 'notebook_path' must be a non-empty string")

        p = Path(notebook_path)
        if not p.is_absolute():
            p = Path(ctx.cwd) / p
        if not p.exists():
            raise FileNotFoundError(f"NotebookEdit: not found: {p}")

        cell_id = tool_input.get("cell_id")
        if cell_id is not None and not isinstance(cell_id, str):
            raise ValueError("NotebookEdit: 'cell_id' must be a string")
        new_source = tool_input.get("new_source", "")
        if new_source is not None and not isinstance(new_source, str):
            raise ValueError("NotebookEdit: 'new_source' must be a string")

        cell_type = tool_input.get("cell_type")
        if cell_type is not None and cell_type not in ("code", "markdown"):
            raise ValueError("NotebookEdit: 'cell_type' must be 'code' or 'markdown'")
        edit_mode = tool_input.get("edit_mode", "replace")
        if edit_mode not in ("replace", "insert", "delete"):
            raise ValueError("NotebookEdit: 'edit_mode' must be 'replace', 'insert', or 'delete'")

        nb = json.loads(p.read_text(encoding="utf-8"))
        cells = nb.get("cells")
        if not isinstance(cells, list):
            raise ValueError("NotebookEdit: invalid notebook: missing 'cells' list")

        def find_index() -> int | None:
            if not cell_id:
                return 0 if cells else None
            for i, c in enumerate(cells):
                if isinstance(c, dict) and c.get("id") == cell_id:
                    return i
            return None

        idx = find_index()

        if edit_mode == "delete":
            if idx is None:
                raise ValueError("NotebookEdit: cell_id not found")
            deleted = cells.pop(idx)
            nb["cells"] = cells
            p.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {
                "message": "Deleted cell",
                "edit_type": "deleted",
                "cell_id": deleted.get("id") if isinstance(deleted, dict) else None,
                "total_cells": len(cells),
            }

        if edit_mode == "insert":
            new_id = cell_id or uuid.uuid4().hex
            cell = {
                "cell_type": cell_type or "code",
                "metadata": {},
                "source": _normalize_source(str(new_source or "")),
                "id": new_id,
            }
            insert_at = (idx + 1) if idx is not None else len(cells)
            cells.insert(insert_at, cell)
            nb["cells"] = cells
            p.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {"message": "Inserted cell", "edit_type": "inserted", "cell_id": new_id, "total_cells": len(cells)}

        # replace
        if idx is None:
            raise ValueError("NotebookEdit: cell_id not found")
        cell = cells[idx]
        if not isinstance(cell, dict):
            raise ValueError("NotebookEdit: invalid cell")
        if cell_type is not None:
            cell["cell_type"] = cell_type
        cell["source"] = _normalize_source(str(new_source or ""))
        cells[idx] = cell
        nb["cells"] = cells
        p.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"message": "Replaced cell", "edit_type": "replaced", "cell_id": cell.get("id"), "total_cells": len(cells)}

