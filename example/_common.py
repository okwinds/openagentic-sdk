from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Awaitable

sys.dont_write_bytecode = True

# When running an example directly, Python sets sys.path[0] to `example/`,
# so `openagentic_sdk` (at repo root) won't be importable unless we add it.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from openagentic_sdk.options import OpenAgenticOptions  # noqa: E402
from openagentic_sdk.permissions.gate import PermissionGate  # noqa: E402
from openagentic_sdk.permissions.interactive import InteractiveApprover  # noqa: E402
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider  # noqa: E402
from openagentic_sdk.permissions.gate import Approver, UserAnswerer  # noqa: E402


def repo_root() -> Path:
    return _REPO_ROOT


def default_session_root() -> Path:
    return repo_root() / ".openagentic-sdk"


def run_sync(coro: Awaitable[Any]) -> Any:
    return asyncio.run(coro)


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if val:
        return val
    raise SystemExit(
        f"Missing required env var: {name}\n"
        "Set RIGHTCODE_API_KEY (and optionally RIGHTCODE_BASE_URL/RIGHTCODE_MODEL/RIGHTCODE_TIMEOUT_S) then rerun."
    )


def require_env_simple(name: str, *, help: str) -> str:
    val = os.environ.get(name)
    if val:
        return val
    raise SystemExit(f"Missing required env var: {name}\n{help}")


def require_command(name: str, *, help: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    raise SystemExit(f"Missing required command: {name}\n{help}")


def example_artifact_dir(example_id: str) -> Path:
    d = default_session_root() / "example-artifacts" / str(example_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def rightcode_provider() -> OpenAICompatibleProvider:
    base_url = os.environ.get("RIGHTCODE_BASE_URL", "https://www.right.codes/codex/v1")
    timeout_s = float(os.environ.get("RIGHTCODE_TIMEOUT_S", "120"))
    max_retries = int(os.environ.get("RIGHTCODE_MAX_RETRIES", "2"))
    retry_backoff_s = float(os.environ.get("RIGHTCODE_RETRY_BACKOFF_S", "0.5"))
    return OpenAICompatibleProvider(
        base_url=base_url,
        timeout_s=timeout_s,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
    )


def rightcode_options(
    *,
    cwd: Path,
    project_dir: Path | None = None,
    session_root: Path | None = None,
    allowed_tools: list[str] | None = None,
    permission_mode: str = "prompt",
    interactive: bool = True,
    approver: Approver | None = None,
    user_answerer: UserAnswerer | None = None,
    ) -> OpenAgenticOptions:
    api_key = require_env("RIGHTCODE_API_KEY")
    model = os.environ.get("RIGHTCODE_MODEL", "gpt-5.2")
    return OpenAgenticOptions(
        provider=rightcode_provider(),
        model=model,
        api_key=api_key,
        cwd=str(cwd),
        project_dir=str(project_dir or cwd),
        session_root=session_root or default_session_root(),
        allowed_tools=allowed_tools,
        permission_gate=PermissionGate(
            permission_mode=permission_mode,
            approver=approver,
            interactive=interactive,
            interactive_approver=InteractiveApprover(input_fn=input) if interactive else None,
            user_answerer=user_answerer,
        ),
        setting_sources=["project"],
    )
