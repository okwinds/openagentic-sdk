from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from _common import EventPrinter, example_debug_enabled, rightcode_options

from open_agent_sdk import query


def _empty_notebook() -> dict:
    return {
        "cells": [],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


async def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        nb_path = root / "report.ipynb"
        nb_path.write_text(json.dumps(_empty_notebook(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        options = rightcode_options(
            cwd=root,
            project_dir=root,
            allowed_tools=["NotebookEdit"],
            permission_mode="bypass",
            interactive=False,
        )
        prompt = (
            "You are generating a notebook report.\n"
            "Call NotebookEdit twice on notebook_path='report.ipynb':\n"
            "1) edit_mode='insert', cell_type='markdown', new_source='## Research Report\\n\\n- Topic: Agent SDK\\n- Summary: ...\\n'\n"
            "2) edit_mode='insert', cell_type='code', new_source='print(\"NOTEBOOK_OK\")'\n"
            "Then reply with NOTEBOOK_EDIT_OK."
        )
        printer = EventPrinter(debug=example_debug_enabled())
        async for ev in query(prompt=prompt, options=options):
            printer.on_event(ev)

        if nb_path.exists():
            print(f"Notebook written: {nb_path}")


if __name__ == "__main__":
    asyncio.run(main())

