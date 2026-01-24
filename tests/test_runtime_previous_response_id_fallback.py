import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openagentic_sdk.events import Result
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.sessions.store import FileSessionStore


class FakeRightcodeStreamingProvider:
    name = "fake-rightcode"

    def __init__(self) -> None:
        self.previous_response_ids: list[str | None] = []

    async def stream(self, *, model, input, tools=(), api_key=None, previous_response_id=None, store=True):
        _ = (model, input, tools, api_key, store)
        self.previous_response_ids.append(previous_response_id)
        if previous_response_id is not None:
            raise RuntimeError(
                'HTTP 400 from https://www.right.codes/codex/v1/responses: {"detail":"Unsupported parameter: previous_response_id"}'
            )
        yield {"type": "text_delta", "delta": "ok"}
        yield {"type": "done"}


class TestRuntimePreviousResponseIdFallback(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_retries_without_previous_response_id_on_unsupported(self) -> None:
        with TemporaryDirectory() as td:
            root = Path(td)
            store = FileSessionStore(root_dir=root)
            sid = store.create_session(metadata={"cwd": str(root)})
            store.append_event(
                sid,
                Result(
                    final_text="previous",
                    session_id=sid,
                    stop_reason="end",
                    response_id="resp_prev",
                ),
            )

            provider = FakeRightcodeStreamingProvider()
            options = OpenAgenticOptions(
                provider=provider,
                model="m",
                api_key="x",
                cwd=str(root),
                permission_gate=PermissionGate(permission_mode="bypass"),
                session_store=store,
                resume=sid,
            )

            import openagentic_sdk

            final = None
            async for e in openagentic_sdk.query(prompt="hi", options=options):
                if getattr(e, "type", None) == "result":
                    final = e

            self.assertEqual(provider.previous_response_ids, ["resp_prev", None])
            self.assertIsNotNone(final)
            self.assertEqual(getattr(final, "final_text", None), "ok")
            pm = getattr(final, "provider_metadata", None)
            self.assertIsInstance(pm, dict)
            self.assertEqual(pm.get("protocol"), "responses")
            self.assertEqual(pm.get("supports_previous_response_id"), False)


if __name__ == "__main__":
    unittest.main()

