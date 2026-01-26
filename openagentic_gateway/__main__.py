from __future__ import annotations

import argparse
import os
import time
from dataclasses import replace
from pathlib import Path

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.paths import default_session_root
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.openai_responses import OpenAIResponsesProvider
from openagentic_sdk.sessions.store import FileSessionStore

from .reply.engine import ReplyEngine
from .server import GatewayServer
from .sessions.session_map import SessionMap


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"Missing required environment variable: {name}")
    return val


def build_gateway_options(*, cwd: str) -> OpenAgenticOptions:
    api_key = _require_env("RIGHTCODE_API_KEY")
    base_url = os.getenv("RIGHTCODE_BASE_URL", "https://www.right.codes/codex/v1")
    model = os.getenv("RIGHTCODE_MODEL", "gpt-5.2")
    timeout_s = _env_float("RIGHTCODE_TIMEOUT_S", 120.0)
    max_retries = _env_int("RIGHTCODE_MAX_RETRIES", 2)
    retry_backoff_s = _env_float("RIGHTCODE_RETRY_BACKOFF_S", 0.5)

    provider = OpenAIResponsesProvider(
        name="openai-compatible",
        base_url=base_url,
        timeout_s=timeout_s,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
    )

    permission_mode = os.getenv("OA_PERMISSION_MODE", "default")
    gate = PermissionGate(permission_mode=permission_mode, interactive=False)

    return OpenAgenticOptions(
        provider=provider,
        model=model,
        api_key=api_key,
        cwd=cwd,
        project_dir=cwd,
        permission_gate=gate,
        setting_sources=["project"],
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="oag", description="OpenAgentic Gateway (Clawdbot-style control plane)")
    p.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=18789, help="Bind port (default: 18789)")
    p.add_argument("--agent-id", default="default", help="Agent id used for routing (default: default)")
    p.add_argument(
        "--agentcore-url",
        default=None,
        help="Optional AgentCore base URL for proxy endpoints (e.g. http://127.0.0.1:4096)",
    )
    p.add_argument(
        "--state-dir",
        default=None,
        help="Gateway state dir (default: $OPENAGENTIC_SDK_HOME/gateway or ~/.openagentic-sdk/gateway)",
    )
    p.add_argument(
        "--exit-after",
        type=float,
        default=None,
        help="Test-only: exit after N seconds (used by unit tests)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)

    cwd = os.getcwd()
    base = Path(ns.state_dir).expanduser() if ns.state_dir else (default_session_root() / "gateway")
    base.mkdir(parents=True, exist_ok=True)

    store = FileSessionStore(root_dir=base / "sessions")
    sm = SessionMap(path=str(base / "session_map.sqlite3"))

    options = build_gateway_options(cwd=cwd)
    options = replace(options, session_store=store)

    engine = ReplyEngine(options=options, session_map=sm, agent_id=str(ns.agent_id))

    server = GatewayServer(
        host=str(ns.host),
        port=int(ns.port),
        agentcore_url=str(ns.agentcore_url) if ns.agentcore_url else None,
        reply_engine=engine,
    )

    server.start()
    try:
        if ns.exit_after is not None:
            time.sleep(max(0.0, float(ns.exit_after)))
            return 0
        while True:
            time.sleep(3600.0)
    except KeyboardInterrupt:
        return 0
    finally:
        server.close()
        sm.close()


if __name__ == "__main__":
    raise SystemExit(main())
