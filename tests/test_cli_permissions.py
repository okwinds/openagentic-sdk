import asyncio
import unittest
from pathlib import Path

from openagentic_cli.permissions import CliPermissionPolicy, build_permission_gate


class TestCliPermissions(unittest.TestCase):
    def test_safe_tools_are_allowed(self) -> None:
        policy = CliPermissionPolicy(
            cwd=Path("."),
            auto_root=Path("."),
            auto_allow_dangerous=False,
            prompt_fn=lambda _p: (_ for _ in ()).throw(AssertionError("should not prompt")),
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(gate.approve("Read", {"file_path": "x"}, context={}))
        self.assertTrue(res.allowed)

    def test_auto_allows_write_in_tree(self) -> None:
        policy = CliPermissionPolicy(
            cwd=Path("/repo"),
            auto_root=Path("/repo"),
            auto_allow_dangerous=True,
            prompt_fn=lambda _p: (_ for _ in ()).throw(AssertionError("should not prompt")),
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(gate.approve("Write", {"file_path": "a.txt", "content": "x", "overwrite": True}, context={}))
        self.assertTrue(res.allowed)

    def test_auto_allows_bash_in_tree(self) -> None:
        policy = CliPermissionPolicy(
            cwd=Path("/repo"),
            auto_root=Path("/repo"),
            auto_allow_dangerous=True,
            prompt_fn=lambda _p: (_ for _ in ()).throw(AssertionError("should not prompt")),
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(gate.approve("Bash", {"command": "pwd"}, context={}))
        self.assertTrue(res.allowed)

    def test_rm_prompts_even_when_auto_allow_enabled(self) -> None:
        asked = {"n": 0}

        def prompt(_p: str) -> bool:
            asked["n"] += 1
            return False

        policy = CliPermissionPolicy(
            cwd=Path("/repo"),
            auto_root=Path("/repo"),
            auto_allow_dangerous=True,
            prompt_fn=prompt,
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(gate.approve("Bash", {"command": "rm -rf ./x"}, context={}))
        self.assertFalse(res.allowed)
        self.assertEqual(asked["n"], 1)

    def test_powershell_remove_item_prompts(self) -> None:
        asked = {"n": 0}

        def prompt(_p: str) -> bool:
            asked["n"] += 1
            return False

        policy = CliPermissionPolicy(
            cwd=Path("/repo"),
            auto_root=Path("/repo"),
            auto_allow_dangerous=True,
            prompt_fn=prompt,
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(
            gate.approve(
                "Bash",
                {"command": "powershell -NoProfile -Command \"Remove-Item -Recurse -Force .\\\\x\""},
                context={},
            )
        )
        self.assertFalse(res.allowed)
        self.assertEqual(asked["n"], 1)

    def test_does_not_auto_allow_write_outside_tree(self) -> None:
        asked = {"n": 0}

        def prompt(_p: str) -> bool:
            asked["n"] += 1
            return False

        policy = CliPermissionPolicy(
            cwd=Path("/repo"),
            auto_root=Path("/repo"),
            auto_allow_dangerous=True,
            prompt_fn=prompt,
        )
        gate = build_permission_gate(policy)
        res = asyncio.run(gate.approve("Write", {"file_path": "/etc/passwd", "content": "x", "overwrite": True}, context={}))
        self.assertFalse(res.allowed)
        self.assertEqual(asked["n"], 1)


if __name__ == "__main__":
    unittest.main()
