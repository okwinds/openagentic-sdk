from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput, ToolCall
from openagentic_sdk.sessions.store import FileSessionStore
from openagentic_sdk.tools.ask_user_question import AskUserQuestionTool
from openagentic_sdk.tools.bash import BashTool
from openagentic_sdk.tools.registry import ToolRegistry


class _ProviderOk:
    name = "acp-test-provider"

    async def complete(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


class _ProviderNeedsPermission:
    name = "acp-test-provider-needs-permission"

    def __init__(self) -> None:
        self._n = 0

    async def complete(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        self._n += 1
        if self._n == 1:
            return ModelOutput(
                assistant_text=None,
                tool_calls=[ToolCall(tool_use_id="t1", name="Bash", arguments={"command": "pwd"})],
                usage={"total_tokens": 1},
                raw=None,
            )
        return ModelOutput(assistant_text="ok", tool_calls=(), usage={"total_tokens": 1}, raw=None)


class _ProviderSlowStream:
    name = "acp-test-provider-slow-stream"

    async def stream(self, *, model, messages, tools=(), api_key=None):  # noqa: ANN001,ANN003
        _ = (model, messages, tools, api_key)
        for _i in range(50):
            await asyncio.sleep(0.05)
            yield {"type": "text_delta", "delta": "x"}
        yield {"type": "done", "response_id": "r1", "usage": {"total_tokens": 1}}


async def _amain() -> None:
    # Use a temp-ish session store under cwd so the subprocess is self-contained.
    root = Path.cwd() / ".acp-test-home"
    store = FileSessionStore(root_dir=root)
    tools = ToolRegistry([BashTool(), AskUserQuestionTool()])

    mode = (os.environ.get("ACP_TEST_MODE") or "ok").strip().lower()
    if mode == "permission":
        provider = _ProviderNeedsPermission()
    elif mode == "slow":
        provider = _ProviderSlowStream()
    else:
        provider = _ProviderOk()

    opts = OpenAgenticOptions(
        provider=provider,
        model="m",
        api_key="x",
        cwd=str(Path.cwd()),
        project_dir=str(Path.cwd()),
        session_store=store,
        tools=tools,
        # ACP server will surface approvals via session/request_permission.
        permission_gate=PermissionGate(permission_mode="prompt", interactive=False),
    )

    from openagentic_sdk.integrations.acp_stdio import serve_acp_stdio

    await serve_acp_stdio(opts)


def main() -> int:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
