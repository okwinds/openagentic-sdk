from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query
from open_agent_sdk.options import AgentDefinition


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = replace(
            rightcode_options(cwd=root, project_dir=root, allowed_tools=["Task"]),
            agents={
                "helper": AgentDefinition(
                    description="Tiny helper agent",
                    prompt="You are the HELPER agent. Reply concisely.",
                    tools=(),
                )
            },
        )

        prompt = (
            "Call the Task tool exactly once with agent='helper' and prompt='Say hi'. "
            "After the tool returns, summarize the child's final_text."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())
