from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query
from open_agent_sdk.events import UserQuestion


async def _answer(question: UserQuestion) -> str:
    prompt = question.prompt.strip()
    choices = question.choices or []
    if choices:
        print(f"{prompt} ({'/'.join(choices)})")
    else:
        print(prompt)
    return input("> ").strip()


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["AskUserQuestion", "TodoWrite"],
            permission_mode="bypass",
            interactive=False,
            user_answerer=_answer,
        )
        prompt = (
            "Ask the user two questions using AskUserQuestion:\n"
            "1) 'What are you building today?'\n"
            "2) 'How much time do you have (minutes)?'\n"
            "Then create a 3-item TODO list using TodoWrite that fits the user's answer.\n"
            "Finally reply with ONBOARDING_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)


if __name__ == "__main__":
    asyncio.run(main())

