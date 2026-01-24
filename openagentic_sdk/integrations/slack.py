from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlackIntegration:
    """Slack compatibility helpers."""

    def format_message(self, *, text: str) -> str:
        return text
