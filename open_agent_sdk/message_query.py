from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator

from .events import AssistantDelta, AssistantMessage as EventAssistantMessage, Result as EventResult, SystemInit, ToolResult, ToolUse
from .messages import AssistantMessage, Message, ResultMessage, StreamEvent, SystemMessage, TextBlock, ToolResultBlock, ToolUseBlock
from .options import OpenAgentOptions
from .runtime import AgentRuntime


def _stringify_tool_output(output: Any) -> str | None:
    if output is None:
        return None
    if isinstance(output, str):
        return output
    try:
        return json.dumps(output, ensure_ascii=False)
    except TypeError:
        return str(output)


async def query_messages(*, prompt: str, options: OpenAgentOptions) -> AsyncIterator[Message]:
    started = time.time()
    runtime = AgentRuntime(options)

    include_partial = bool(getattr(options, "include_partial_messages", False))
    session_id = options.resume or ""
    steps = 0
    async for e in runtime.query(prompt):
        if isinstance(e, SystemInit):
            session_id = e.session_id
            yield SystemMessage(subtype="system.init", data={"session_id": e.session_id, "cwd": e.cwd, "sdk_version": e.sdk_version})
        elif include_partial and isinstance(e, AssistantDelta):
            yield StreamEvent(
                uuid=uuid.uuid4().hex,
                session_id=session_id,
                event={"type": "text_delta", "delta": e.text_delta},
                parent_tool_use_id=e.parent_tool_use_id,
            )
        elif isinstance(e, ToolUse):
            yield AssistantMessage(
                content=[ToolUseBlock(id=e.tool_use_id, name=e.name, input=dict(e.input or {}))],
                model=options.model,
            )
        elif isinstance(e, ToolResult):
            yield AssistantMessage(
                content=[
                    ToolResultBlock(
                        tool_use_id=e.tool_use_id,
                        content=_stringify_tool_output(e.output),
                        is_error=e.is_error,
                    )
                ],
                model=options.model,
            )
        elif isinstance(e, EventAssistantMessage):
            yield AssistantMessage(content=[TextBlock(text=e.text)], model=options.model)
        elif isinstance(e, EventResult):
            steps = int(e.steps or steps)
            elapsed_ms = int((time.time() - started) * 1000)
            stop_reason = (e.stop_reason or "").strip()
            is_error = stop_reason not in ("", "end")
            yield ResultMessage(
                subtype="error" if is_error else "success",
                duration_ms=elapsed_ms,
                duration_api_ms=0,
                is_error=is_error,
                num_turns=1,
                session_id=e.session_id,
                total_cost_usd=None,
                usage=(dict(e.usage) if isinstance(e.usage, dict) else None),
                result=e.final_text,
                structured_output=None,
            )

