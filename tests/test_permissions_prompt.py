import unittest

from open_agent_sdk.permissions.gate import PermissionGate


class TestPermissionsPrompt(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_denies_on_no(self) -> None:
        from open_agent_sdk.permissions.interactive import InteractiveApprover

        approver = InteractiveApprover(input_fn=lambda _: "no")
        gate = PermissionGate(permission_mode="prompt", interactive=True, interactive_approver=approver)
        result = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertFalse(result.allowed)

    async def test_prompt_allows_on_yes(self) -> None:
        from open_agent_sdk.permissions.interactive import InteractiveApprover

        approver = InteractiveApprover(input_fn=lambda _: "yes")
        gate = PermissionGate(permission_mode="prompt", interactive=True, interactive_approver=approver)
        result = await gate.approve("Bash", {"command": "echo hi"}, context={})
        self.assertTrue(result.allowed)


if __name__ == "__main__":
    unittest.main()
