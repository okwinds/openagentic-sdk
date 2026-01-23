from __future__ import annotations

import asyncio
import json

from _common import example_debug_enabled, repo_root, rightcode_options

from open_agent_sdk.client import OpenAgentSDKClient
from open_agent_sdk.messages import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock


def _try_parse_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


async def main() -> None:
    options = rightcode_options(
        cwd=repo_root(),
        project_dir=repo_root(),
        allowed_tools=["TodoWrite"],
        permission_mode="bypass",
        interactive=False,
    )
    debug = example_debug_enabled()

    async with OpenAgentSDKClient(options) as client:
        todo_inputs: dict[str, list[dict]] = {}

        async def _run_turn(prompt: str) -> ResultMessage:
            await client.query(prompt)
            result: ResultMessage | None = None
            async for m in client.receive_response():
                if isinstance(m, AssistantMessage):
                    for b in m.content:
                        if isinstance(b, ToolUseBlock) and b.name == "TodoWrite":
                            todos = b.input.get("todos") if isinstance(b.input, dict) else None
                            if isinstance(todos, list):
                                todo_inputs[b.id] = [dict(x) for x in todos if isinstance(x, dict)]
                        if isinstance(b, ToolResultBlock):
                            tool_use_id = b.tool_use_id
                            if tool_use_id and tool_use_id in todo_inputs:
                                out = _try_parse_json(b.content if isinstance(b.content, str) else None)
                                stats = out.get("stats") if isinstance(out, dict) else None
                                if isinstance(stats, dict):
                                    print(
                                        "TODOs:",
                                        f"total={stats.get('total')}",
                                        f"pending={stats.get('pending')}",
                                        f"in_progress={stats.get('in_progress')}",
                                        f"completed={stats.get('completed')}",
                                    )
                                else:
                                    print("TODOs updated")
                                for item in todo_inputs.get(tool_use_id) or []:
                                    status = item.get("status") or "pending"
                                    text = item.get("activeForm") or item.get("content") or ""
                                    print(f"- [{status}] {text}")
                if isinstance(m, ResultMessage):
                    result = m
            if result is None:
                raise RuntimeError("No ResultMessage received")
            return result

        r1 = await _run_turn(
            "Create a 3-item TODO list for 'write a weekly status update' using TodoWrite. Then say TURN1_OK."
        )
        print(r1.result or "")
        if debug:
            print(f"[debug] session_id={r1.session_id}")

        r2 = await _run_turn("Update the TODOs: mark one completed via TodoWrite. Then say TURN2_OK.")
        print(r2.result or "")
        if debug:
            print(f"[debug] session_id={r2.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
