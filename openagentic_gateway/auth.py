from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AuthDecision:
    allowed: bool
    status: int = 200
    error: str | None = None


def _extract_bearer_token(headers: Mapping[str, str]) -> str | None:
    raw = (headers.get("Authorization") or "").strip()
    if not raw:
        return None
    if not raw.lower().startswith("bearer "):
        return None
    token = raw.split(" ", 1)[1].strip()
    return token or None


@dataclass(frozen=True, slots=True)
class GatewayAuthConfig:
    operator_token: str | None = None

    @staticmethod
    def from_env() -> "GatewayAuthConfig":
        tok = (os.environ.get("OA_GATEWAY_TOKEN") or "").strip()
        return GatewayAuthConfig(operator_token=tok or None)


def authorize_path(*, path: str, headers: Mapping[str, str], cfg: GatewayAuthConfig) -> AuthDecision:
    # /health is always public (dev-friendly).
    if path == "/health":
        return AuthDecision(allowed=True)

    # If no token configured, treat as dev mode and allow everything (v1).
    if not cfg.operator_token:
        return AuthDecision(allowed=True)

    # Protect operator APIs.
    if path.startswith("/v1/"):
        token = _extract_bearer_token(headers)
        if token != cfg.operator_token:
            return AuthDecision(allowed=False, status=401, error="unauthorized")
        return AuthDecision(allowed=True)

    return AuthDecision(allowed=True)

