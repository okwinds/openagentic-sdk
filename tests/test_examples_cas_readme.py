from __future__ import annotations

import unittest
from pathlib import Path


class TestExamplesCasReadme(unittest.TestCase):
    def test_readme_lists_cas_scenario_scripts(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        readme = (repo_root / "example" / "README.md").read_text(encoding="utf-8", errors="replace")

        expected = [
            "cas_01_quickstart.py",
            "cas_02_client_streaming_and_multiturn.py",
            "cas_03_interrupt.py",
            "cas_04_permissions_callback.py",
            "cas_05_hooks.py",
            "cas_06_include_partial_messages.py",
            "cas_07_sdk_mcp_tools.py",
            "cas_08_task_subagent.py",
        ]
        for name in expected:
            with self.subTest(name=name):
                self.assertIn(name, readme)


if __name__ == "__main__":
    unittest.main()

