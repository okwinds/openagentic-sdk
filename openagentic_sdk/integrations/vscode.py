from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VSCodeIntegration:
    """VSCode compatibility helpers."""

    def workspace_hint(self, *, project_dir: str) -> str:
        return f"Open this folder in VSCode: {project_dir}"
