import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.tools.base import ToolContext
from openagentic_sdk.tools.notebook_edit import NotebookEditTool


class TestNotebookEdit(unittest.TestCase):
    def test_replaces_cell_source(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            nb_path = root / "a.ipynb"
            nb = {
                "cells": [
                    {
                        "cell_type": "code",
                        "metadata": {},
                        "source": ["print(1)\n"],
                        "id": "c1",
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
            nb_path.write_text(json.dumps(nb), encoding="utf-8")

            tool = NotebookEditTool()
            out = tool.run_sync(
                {"notebook_path": str(nb_path), "cell_id": "c1", "new_source": "print(2)", "edit_mode": "replace"},
                ToolContext(cwd=str(root)),
            )
            self.assertEqual(out["edit_type"], "replaced")

            nb2 = json.loads(nb_path.read_text(encoding="utf-8"))
            self.assertIn("print(2)", "".join(nb2["cells"][0]["source"]))


if __name__ == "__main__":
    unittest.main()

