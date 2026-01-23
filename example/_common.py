from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Awaitable, Mapping, Sequence

sys.dont_write_bytecode = True

# When running an example directly, Python sets sys.path[0] to `example/`,
# so `open_agent_sdk` (at repo root) won't be importable unless we add it.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from open_agent_sdk.options import OpenAgentOptions  # noqa: E402
from open_agent_sdk.permissions.gate import PermissionGate  # noqa: E402
from open_agent_sdk.permissions.interactive import InteractiveApprover  # noqa: E402
from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider  # noqa: E402
from open_agent_sdk.permissions.gate import Approver, UserAnswerer  # noqa: E402


def repo_root() -> Path:
    return _REPO_ROOT


def default_session_root() -> Path:
    return repo_root() / ".open-agent-sdk"


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
    return OpenAICompatibleProvider(base_url=base_url, timeout_s=timeout_s)


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
) -> OpenAgentOptions:
    api_key = require_env("RIGHTCODE_API_KEY")
    model = os.environ.get("RIGHTCODE_MODEL", "gpt-5.2")
    return OpenAgentOptions(
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


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def example_debug_enabled(argv: Sequence[str] | None = None) -> bool:
    argv2 = list(sys.argv[1:] if argv is None else argv)
    return env_bool("OPEN_AGENT_SDK_EXAMPLE_DEBUG", False) or ("--debug" in argv2)


class EventPrinter:
    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug
        self._saw_delta = False

    def on_event(self, ev: Any) -> None:
        t = getattr(ev, "type", None)
        if t == "assistant.delta":
            delta = getattr(ev, "text_delta", "")
            if isinstance(delta, str) and delta:
                print(delta, end="", flush=True)
                self._saw_delta = True
            return

        if t == "assistant.message":
            text = getattr(ev, "text", "")
            if not isinstance(text, str) or not text:
                return
            if self._saw_delta:
                print()
                self._saw_delta = False
            agent = getattr(ev, "agent_name", None)
            prefix = f"[{agent}] " if isinstance(agent, str) and agent else ""
            print(prefix + text)
            return

        if t == "user.question":
            prompt = getattr(ev, "prompt", "")
            choices = getattr(ev, "choices", None)
            if isinstance(prompt, str) and prompt:
                if isinstance(choices, list) and choices:
                    print(f"[question] {prompt} choices={choices}")
                else:
                    print(f"[question] {prompt}")
            return

        if not self._debug:
            return

        if t == "tool.use":
            name = getattr(ev, "name", "")
            tool_input = getattr(ev, "input", None)
            agent = getattr(ev, "agent_name", None)
            prefix = f"[{agent}] " if isinstance(agent, str) and agent else ""
            if isinstance(name, str) and name:
                if isinstance(tool_input, dict) and tool_input:
                    print(f"{prefix}[tool] {name} {tool_input}")
                else:
                    print(f"{prefix}[tool] {name}")
            return

        if t == "tool.result":
            tool_use_id = getattr(ev, "tool_use_id", "")
            is_error = bool(getattr(ev, "is_error", False))
            error_message = getattr(ev, "error_message", None)
            status = "error" if is_error else "ok"
            if isinstance(tool_use_id, str) and tool_use_id:
                line = f"[tool.result] {tool_use_id} {status}"
            else:
                line = f"[tool.result] {status}"
            if is_error and isinstance(error_message, str) and error_message:
                line += f" msg={error_message!r}"
            print(line)
            return

        if t == "hook.event":
            name = getattr(ev, "name", "")
            hook_point = getattr(ev, "hook_point", "")
            action = getattr(ev, "action", None)
            matched = getattr(ev, "matched", None)
            line = f"[hook] {hook_point}:{name}"
            if action is not None:
                line += f" action={action}"
            if matched is not None:
                line += f" matched={matched}"
            print(line)
            return

        if t == "skill.activated":
            name = getattr(ev, "name", "")
            if isinstance(name, str) and name:
                print(f"[skill] activated {name}")
            return

        if t == "result":
            stop_reason = getattr(ev, "stop_reason", None)
            session_id = getattr(ev, "session_id", None)
            line = "[done]"
            if isinstance(stop_reason, str) and stop_reason:
                line += f" stop_reason={stop_reason}"
            if isinstance(session_id, str) and session_id:
                line += f" session_id={session_id}"
            print(line)
            return
