from __future__ import annotations

import asyncio
import json

from _common import example_artifact_dir, repo_root, rightcode_options
from openagentic_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


def _empty_notebook() -> dict:
    return {
        "cells": [],
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


async def main() -> None:
    out_dir = example_artifact_dir("24")
    nb_path = out_dir / "report.ipynb"
    nb_path.write_text(json.dumps(_empty_notebook(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    options = rightcode_options(
        cwd=out_dir,
        project_dir=repo_root(),
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
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)

    print(f"Wrote: {nb_path}")


if __name__ == "__main__":
    asyncio.run(main())
