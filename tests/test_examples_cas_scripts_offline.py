from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class TestExamplesCasScriptsOffline(unittest.TestCase):
    def test_cas_01_quickstart_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_01_quickstart"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_02_client_streaming_and_multiturn_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [
                sys.executable,
                "scripts/verify_examples.py",
                "--offline",
                "--only",
                "cas_02_client_streaming_and_multiturn",
            ],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_03_interrupt_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_03_interrupt"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_04_permissions_callback_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_04_permissions_callback"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_05_hooks_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_05_hooks"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_06_include_partial_messages_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_06_include_partial_messages"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_07_sdk_mcp_tools_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_07_sdk_mcp_tools"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")

    def test_cas_08_task_subagent_offline_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")

        proc = subprocess.run(
            [sys.executable, "scripts/verify_examples.py", "--offline", "--only", "cas_08_task_subagent"],
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            self.fail(f"verify_examples failed (exit={proc.returncode}):\n{proc.stdout}")


if __name__ == "__main__":
    unittest.main()
