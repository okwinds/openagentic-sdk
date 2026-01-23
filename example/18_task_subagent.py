from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query
from openagentic_sdk.options import AgentDefinition


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
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
