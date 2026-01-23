from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        nb_path = root / "tutorial.ipynb"
        nb = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# Tutorial\n", "\n", "TODO: fill in.\n"],
                    "id": "cell-1",
                }
            ],
            "metadata": {"language_info": {"name": "python"}},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["NotebookEdit"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "Update the notebook tutorial.\n"
            "1) Use NotebookEdit edit_mode='replace' on notebook_path='tutorial.ipynb' (replace the first cell) "
            "to explain what an agent loop is in 3 bullet points.\n"
            "2) Use NotebookEdit edit_mode='insert' to add a code cell that prints 'TUTORIAL_OK'.\n"
            "Finally reply with TUTORIAL_BUILDER_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        print(f"Notebook updated: {nb_path}")


if __name__ == "__main__":
    asyncio.run(main())

