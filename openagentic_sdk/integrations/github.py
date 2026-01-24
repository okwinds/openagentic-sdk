from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitHubIntegration:
    """GitHub integration helpers.

    This module intentionally does not perform network actions by default.
    """

    def format_pull_request_body(self, *, summary: str, testing: str | None = None) -> str:
        lines: list[str] = ["## Summary", summary.strip()]
        if testing and testing.strip():
            lines.extend(["", "## Testing", testing.strip()])
        return "\n".join(lines).strip() + "\n"
