import asyncio
import os
import sys

sys.dont_write_bytecode = True

from pathlib import Path

# When running this file directly, Python sets sys.path[0] to `example/`,
# so `open_agent_sdk` (at repo root) won't be importable unless we add it.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from open_agent_sdk import OpenAgentOptions, query
from open_agent_sdk.permissions.gate import PermissionGate
from open_agent_sdk.permissions.interactive import InteractiveApprover
from open_agent_sdk.providers.openai_compatible import OpenAICompatibleProvider


async def main() -> None:
    session_root = _REPO_ROOT / ".open-agent-sdk"
    base_url = os.environ.get("RIGHTCODE_BASE_URL", "https://www.right.codes/codex/v1")
    timeout_s = float(os.environ.get("RIGHTCODE_TIMEOUT_S", "120"))
    options = OpenAgentOptions(
        provider=OpenAICompatibleProvider(base_url=base_url, timeout_s=timeout_s),
        model=os.environ.get("RIGHTCODE_MODEL", "gpt-5.2"),
        api_key=os.environ.get("RIGHTCODE_API_KEY"),
        cwd=str(_REPO_ROOT),
        project_dir=str(_REPO_ROOT),
        session_root=session_root,
        allowed_tools=["Read", "Edit", "Bash"],
        permission_gate=PermissionGate(
            permission_mode="prompt",
            interactive=True,
            interactive_approver=InteractiveApprover(input_fn=input),
        ),
        setting_sources=["project"],
    )

    async for event in query(prompt="Find and fix the bug in auth.py", options=options):
        if event.type == "assistant.delta":
            print(event.text_delta, end="", flush=True)
        elif event.type == "assistant.message":
            print()
            print(event.text)
        elif event.type == "tool.use":
            print(f"\n[tool.use] {event.name} {event.input}")
        elif event.type == "tool.result":
            print(f"[tool.result] {event.tool_use_id} error={event.is_error}")
        elif event.type == "result":
            print(f"\n[result] session_id={event.session_id} stop_reason={event.stop_reason}")


if __name__ == "__main__":
    asyncio.run(main())
