from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ACPIntegration:
    """Agent Client Protocol (ACP) compatibility helpers."""

    def protocol_name(self) -> str:
        return "acp"
