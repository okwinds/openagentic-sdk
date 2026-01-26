from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from openagentic_sdk.hooks.engine import HookEngine
from openagentic_sdk.options import AgentDefinition, OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.openai_responses import OpenAIResponsesProvider
from openagentic_sdk.sessions.store import FileSessionStore


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if v:
        return v
    raise RuntimeError(
        f"Missing required env var: {name}\n"
        "These are real-network e2e tests.\n"
        "Set RIGHTCODE_API_KEY (and optionally RIGHTCODE_BASE_URL/RIGHTCODE_MODEL/RIGHTCODE_TIMEOUT_S) then rerun."
    )


def _env_str(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v.strip() else default


def _env_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None or not v.strip():
        return default
    try:
        return float(v)
    except ValueError:
        return default


def make_provider() -> OpenAIResponsesProvider:
    base_url = _env_str("RIGHTCODE_BASE_URL", "https://www.right.codes/codex/v1")
    timeout_s = _env_float("RIGHTCODE_TIMEOUT_S", 120.0)
    max_retries = int(_env_str("RIGHTCODE_MAX_RETRIES", "2"))
    retry_backoff_s = _env_float("RIGHTCODE_RETRY_BACKOFF_S", 0.5)
    return OpenAIResponsesProvider(
        name="openai-compatible",
        base_url=base_url,
        timeout_s=timeout_s,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
    )


def make_options(
    root: Path,
    *,
    allowed_tools: Sequence[str] | None,
    include_partial_messages: bool = False,
    hooks: HookEngine | None = None,
    mcp_servers: Mapping[str, Any] | None = None,
    agents: Mapping[str, AgentDefinition] | None = None,
) -> OpenAgenticOptions:
    api_key = require_env("RIGHTCODE_API_KEY")
    model = _env_str("RIGHTCODE_MODEL", "gpt-5.2")
    store = FileSessionStore(root_dir=root)

    opts = OpenAgenticOptions(
        provider=make_provider(),
        model=model,
        api_key=api_key,
        cwd=str(root),
        project_dir=str(root),
        session_store=store,
        permission_gate=PermissionGate(permission_mode="bypass"),
        allowed_tools=list(allowed_tools) if allowed_tools is not None else None,
        include_partial_messages=include_partial_messages,
        hooks=hooks or HookEngine(),
        mcp_servers=dict(mcp_servers) if mcp_servers is not None else None,
        agents=dict(agents) if agents is not None else {},
    )
    return replace(opts, max_steps=30)

