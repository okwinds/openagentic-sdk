from __future__ import annotations

import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import openagentic_sdk
from openagentic_sdk.permissions.cas import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext
from openagentic_sdk.permissions.gate import PermissionGate

from e2e_tests._harness import make_options


class TestE2EPermissionsCallback(unittest.IsolatedAsyncioTestCase):
    async def test_can_use_tool_callback_is_invoked(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            fixture = f"PUBLIC_FIXTURE_{uuid.uuid4().hex}"
            (root / "fixture.txt").write_text(fixture, encoding="utf-8")
            expected_len = len(fixture)

            invocations: list[str] = []

            async def can_use_tool(
                tool_name: str,
                input_data: dict[str, Any],  # noqa: ARG001
                context: ToolPermissionContext,  # noqa: ARG001
            ) -> PermissionResultAllow | PermissionResultDeny:
                invocations.append(tool_name)
                return PermissionResultAllow()

            opts0 = make_options(root, allowed_tools=["Read"])
            gate = PermissionGate(permission_mode="default", can_use_tool=can_use_tool, interactive=False)
            opts = replace(opts0, permission_gate=gate)

            prompt = (
                "Use the Read tool to read ./fixture.txt.\n"
                "Compute the number of characters in the file content.\n"
                f"Reply with exactly: COUNT:{expected_len}"
            )

            events: list[object] = []
            async for ev in openagentic_sdk.query(prompt=prompt, options=opts):
                events.append(ev)

            self.assertIn("Read", invocations)
            final_texts = [getattr(e, "final_text", "") for e in events if getattr(e, "type", None) == "result"]
            final_text = final_texts[-1] if final_texts else ""
            self.assertIn(f"COUNT:{expected_len}", final_text)


if __name__ == "__main__":
    unittest.main()
