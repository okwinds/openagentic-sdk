from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options

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
        async for ev in query(prompt=prompt, options=options):
            if ev.type in ("tool.use", "tool.result", "assistant.message", "result"):
                # Events include agent_name / parent_tool_use_id for subagent linkage.
                print(f"[{ev.type}] agent={getattr(ev, 'agent_name', None)} parent={getattr(ev, 'parent_tool_use_id', None)}")
                if ev.type == "assistant.message":
                    print(f"  text={ev.text!r}")
                else:
                    print(f"  {ev}")


if __name__ == "__main__":
    asyncio.run(main())
