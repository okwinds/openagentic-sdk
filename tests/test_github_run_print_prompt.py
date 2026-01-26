from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class TestGithubRunPrintPrompt(unittest.TestCase):
    def test_print_prompt_issue_comment(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            event_path = root / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "comment": {"body": "hello"},
                        "issue": {"title": "Bug", "html_url": "https://example.invalid/1"},
                    }
                ),
                encoding="utf-8",
            )

            env = dict(os.environ)
            # The subprocess runs outside the repo cwd; ensure it can import the package.
            repo_root = Path(__file__).resolve().parents[1]
            env["PYTHONPATH"] = os.fspath(repo_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            env["GITHUB_EVENT_NAME"] = "issue_comment"
            env["GITHUB_REPOSITORY"] = "o/a"
            env["GITHUB_RUN_ID"] = "1"
            env.pop("RIGHTCODE_API_KEY", None)

            proc = subprocess.run(
                [sys.executable, "-m", "openagentic_cli", "github", "run", "--print-prompt", "--event-path", os.fspath(event_path)],
                cwd=os.fspath(root),
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            out = proc.stdout
            self.assertIn("issue comment", out)
            self.assertIn("Bug", out)
            self.assertIn("hello", out)


if __name__ == "__main__":
    unittest.main()
