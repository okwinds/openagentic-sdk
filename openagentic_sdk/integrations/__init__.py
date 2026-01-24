from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntegrationInfo:
    name: str
    description: str


def list_integrations() -> list[IntegrationInfo]:
    # Keep this lightweight: integrations are optional and may require external
    # binaries/tokens at runtime.
    return [
        IntegrationInfo(name="github", description="GitHub helper surfaces (no network by default)."),
        IntegrationInfo(name="vscode", description="VSCode compatibility helpers."),
        IntegrationInfo(name="slack", description="Slack compatibility helpers."),
        IntegrationInfo(name="acp", description="Agent Client Protocol (ACP) compatibility helpers."),
    ]
