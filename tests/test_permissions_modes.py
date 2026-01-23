import unittest

from openagentic_sdk.permissions.cas import PermissionResultAllow, PermissionResultDeny
from openagentic_sdk.permissions.gate import PermissionGate


class TestPermissionModes(unittest.IsolatedAsyncioTestCase):
    async def test_accept_edits_allows_edit_and_write(self) -> None:
        gate = PermissionGate(permission_mode="acceptEdits", interactive=False)
        self.assertTrue((await gate.approve("Edit", {"file_path": "x"}, context={})).allowed)
        self.assertTrue((await gate.approve("Write", {"file_path": "x"}, context={})).allowed)

    async def test_plan_denies(self) -> None:
        gate = PermissionGate(permission_mode="plan")
        self.assertFalse((await gate.approve("Read", {"file_path": "x"}, context={})).allowed)

    async def test_bypass_permissions_allows(self) -> None:
        gate = PermissionGate(permission_mode="bypassPermissions")
        self.assertTrue((await gate.approve("Bash", {"command": "echo hi"}, context={})).allowed)

    async def test_default_allows_safe_tools_and_prompts_for_unsafe(self) -> None:
        gate = PermissionGate(permission_mode="default", interactive=False)
        self.assertTrue((await gate.approve("Read", {"file_path": "x"}, context={})).allowed)
        res = await gate.approve("Bash", {"command": "echo hi"}, context={"tool_use_id": "t1"})
        self.assertFalse(res.allowed)
        self.assertIsNotNone(res.question)

    async def test_can_use_tool_can_rewrite_input(self) -> None:
        async def can_use_tool(tool_name, input_data, context):  # noqa: ANN001
            _ = (tool_name, context)
            return PermissionResultAllow(updated_input={**input_data, "command": "echo rewritten"})

        gate = PermissionGate(permission_mode="default", can_use_tool=can_use_tool, interactive=False)
        res = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertTrue(res.allowed)
        self.assertEqual(res.updated_input["command"], "echo rewritten")  # type: ignore[index]

    async def test_can_use_tool_can_deny_with_message(self) -> None:
        async def can_use_tool(tool_name, input_data, context):  # noqa: ANN001
            _ = (tool_name, input_data, context)
            return PermissionResultDeny(message="nope", interrupt=False)

        gate = PermissionGate(permission_mode="default", can_use_tool=can_use_tool, interactive=False)
        res = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertFalse(res.allowed)
        self.assertEqual(res.deny_message, "nope")


if __name__ == "__main__":
    unittest.main()

