from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query
from open_agent_sdk.hooks.engine import HookEngine
from open_agent_sdk.hooks.models import HookDecision, HookMatcher


async def _redact(payload):
    out = payload.get("tool_output")
    if not isinstance(out, dict):
        return HookDecision()
    content = out.get("content")
    if not isinstance(content, str) or not content:
        return HookDecision()
    redacted = content.replace("SECRET_TOKEN_123", "[REDACTED]")
    out2 = dict(out)
    out2["content"] = redacted
    return HookDecision(override_tool_output=out2, action="redact")


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        (root / "secrets.txt").write_text("api_key=SECRET_TOKEN_123\n", encoding="utf-8")

        hooks = HookEngine(post_tool_use=[HookMatcher(name="redact-read", tool_name_pattern="Read", hook=_redact)])
        options = replace(
            rightcode_options(
                cwd=root,
                project_dir=root,
                allowed_tools=["Read"],
                permission_mode="bypass",
                interactive=False,
            ),
            hooks=hooks,
        )
        prompt = "Use Read to read secrets.txt, then reply with REDACT_OK and show the content you saw."
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())

