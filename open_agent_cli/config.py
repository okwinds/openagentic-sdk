from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from open_agent_sdk.options import OpenAgentOptions
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.permissions.interactive import InteractiveApprover
from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"Missing required environment variable: {name}")
    return val


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise SystemExit(f"Invalid {name}={raw!r}; expected int") from e


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise SystemExit(f"Invalid {name}={raw!r}; expected float") from e


def build_provider_rightcode() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="rightcode",
        base_url=os.getenv("RIGHTCODE_BASE_URL", "https://www.right.codes/codex/v1"),
        timeout_s=_env_float("RIGHTCODE_TIMEOUT_S", 120.0),
        max_retries=_env_int("RIGHTCODE_MAX_RETRIES", 2),
        retry_backoff_s=_env_float("RIGHTCODE_RETRY_BACKOFF_S", 0.5),
    )


def build_options(
    *,
    cwd: str,
    project_dir: str | None,
    permission_mode: str,
    allowed_tools: Sequence[str] | None = None,
    session_root: str | Path | None = None,
    resume: str | None = None,
    interactive: bool = False,
) -> OpenAgentOptions:
    session_root_path: Path | None = None
    if session_root is not None:
        session_root_path = Path(session_root)

    gate = PermissionGate(
        permission_mode=permission_mode,
        interactive=interactive,
        interactive_approver=InteractiveApprover(input_fn=input) if interactive else None,
    )

    return OpenAgentOptions(
        provider=build_provider_rightcode(),
        api_key=require_env("RIGHTCODE_API_KEY"),
        model=os.getenv("RIGHTCODE_MODEL", "gpt-5.2"),
        cwd=cwd,
        project_dir=project_dir,
        allowed_tools=allowed_tools,
        permission_gate=gate,
        session_root=session_root_path,
        resume=resume,
        setting_sources=["project"],
    )
