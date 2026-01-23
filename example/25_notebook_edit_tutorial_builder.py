from __future__ import annotations

import asyncio
import json

from _common import example_artifact_dir, repo_root, rightcode_options
from open_agent_sdk.console import ConsoleRenderer, console_debug_enabled, console_query


async def main() -> None:
    out_dir = example_artifact_dir("25")
    nb_path = out_dir / "tutorial.ipynb"
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
        cwd=out_dir,
        project_dir=repo_root(),
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
    printer = ConsoleRenderer(debug=console_debug_enabled())
    await console_query(prompt=prompt, options=options, renderer=printer)

    print(f"Wrote: {nb_path}")


if __name__ == "__main__":
    asyncio.run(main())
