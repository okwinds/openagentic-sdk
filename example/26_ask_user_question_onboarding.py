from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query
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
        printer = ConsoleRenderer(debug=console_debug_enabled())
        await console_query(prompt=prompt, options=options, renderer=printer)


if __name__ == "__main__":
    asyncio.run(main())
