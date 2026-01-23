from __future__ import annotations

import json
import os
import sys
from typing import TextIO

from open_agent_sdk.api import run
from open_agent_sdk.console.renderer import ConsoleRenderer
from open_agent_sdk.console.run import console_query
from open_agent_sdk.options import OpenAgentOptions

from .style import InlineCodeHighlighter, StyleConfig, StylizingStream, should_colorize


def format_run_json(*, final_text: str, session_id: str, stop_reason: str | None) -> str:
    return json.dumps(
        {
            "final_text": final_text,
            "session_id": session_id,
            "stop_reason": stop_reason,
        },
        ensure_ascii=False,
    )


async def run_once(
    options: OpenAgentOptions,
    prompt: str,
    *,
    stream: bool,
    json_output: bool,
    stdout: TextIO | None = None,
    color_config: StyleConfig | None = None,
) -> int:
    out = stdout or sys.stdout
    if json_output:
        res = await run(prompt=prompt, options=options)
        stop_reason: str | None = None
        for e in res.events:
            if getattr(e, "type", None) == "result":
                stop_reason = getattr(e, "stop_reason", None)
        out.write(format_run_json(final_text=res.final_text, session_id=res.session_id, stop_reason=stop_reason) + "\n")
        out.flush()
        return 0

    if stream:
        cfg = color_config or StyleConfig(color="auto")
        enable_color = should_colorize(cfg, isatty=getattr(out, "isatty", lambda: False)(), platform=sys.platform)
        stream2 = StylizingStream(out, highlighter=InlineCodeHighlighter(enabled=enable_color)) if enable_color else out
        renderer = ConsoleRenderer(stream=stream2, debug=False)
        await console_query(prompt=prompt, options=options, renderer=renderer)
        return 0

    res = await run(prompt=prompt, options=options)
    out.write((res.final_text or "") + "\n")
    out.flush()
    return 0
