import unittest

from openagentic_sdk.permissions.gate import PermissionGate


class TestPermissionGate(unittest.IsolatedAsyncioTestCase):
    async def test_gate_denies_when_callback_returns_false(self) -> None:
        async def approver(tool_name, tool_input, context):
            return False

        gate = PermissionGate(permission_mode="callback", approver=approver, interactive=False)
        result = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertFalse(result.allowed)

    async def test_gate_allows_when_bypass(self) -> None:
        gate = PermissionGate(permission_mode="bypass")
        result = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
