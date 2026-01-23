import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.options import OpenAgentOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.base import ModelOutput
from openagentic_sdk.sessions.store import FileSessionStore


class NoopProvider:
    name = "noop"

    async def complete(self, *, model, messages, tools=(), api_key=None):
        return ModelOutput(assistant_text="ok", tool_calls=[])


class TestSessionMeta(unittest.IsolatedAsyncioTestCase):
    async def test_meta_written(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            options = OpenAgentOptions(
                provider=NoopProvider(),
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
            )
            import openagentic_sdk

            events = []
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                events.append(e)
            sid = next(e.session_id for e in events if getattr(e, "type", None) == "system.init")
            meta = json.loads((root / "sessions" / sid / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["metadata"]["cwd"], str(root))
            self.assertEqual(meta["metadata"]["provider_name"], "noop")
            self.assertEqual(meta["metadata"]["model"], "m")


if __name__ == "__main__":
    unittest.main()

