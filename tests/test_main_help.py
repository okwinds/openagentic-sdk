import os
import subprocess
import sys
import unittest
from pathlib import Path


class TestMainHelp(unittest.TestCase):
    def test_help(self) -> None:
        env = dict(os.environ)
        project_root = Path(__file__).resolve().parents[1]
        env["PYTHONPATH"] = str(project_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        proc = subprocess.run(
            [sys.executable, "-m", "openagentic_sdk", "--help"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("openagentic", (proc.stdout + proc.stderr).lower())


if __name__ == "__main__":
    unittest.main()
