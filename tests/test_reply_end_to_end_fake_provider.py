import tempfile
import unittest
from pathlib import Path


class _FakeResponsesProvider:
    name = "fake"

    async def complete(self, *, model, input, **kwargs):  # noqa: A002
        from openagentic_sdk.providers.base import ModelOutput

        return ModelOutput(assistant_text="hi from fake", tool_calls=(), provider_metadata={"protocol": "responses"})


class TestReplyEndToEndFakeProvider(unittest.TestCase):
    def test_inbound_runs_agent_and_returns_text_payload(self) -> None:
        import asyncio

        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.permissions.gate import PermissionGate
        from openagentic_sdk.sessions.store import FileSessionStore

        from openagentic_gateway.reply.envelope import InboundEnvelope
        from openagentic_gateway.reply.engine import ReplyEngine
        from openagentic_gateway.sessions.session_map import SessionMap

        async def _run() -> None:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                store = FileSessionStore(root_dir=root / "sessions")
                sm = SessionMap(path=str(root / "session_map.sqlite3"))
                opts = OpenAgenticOptions(
                    provider=_FakeResponsesProvider(),
                    model="fake-model",
                    api_key=None,
                    permission_gate=PermissionGate(permission_mode="deny"),
                    session_store=store,
                    setting_sources=[],
                )
                engine = ReplyEngine(options=opts, session_map=sm, agent_id="agent1")

                env = InboundEnvelope(
                    channel="telegram",
                    account_id="acc",
                    peer_kind="dm",
                    peer_id="user123",
                    text="ping",
                )
                out1 = await engine.get_reply(env)
                self.assertEqual([p.kind for p in out1.payloads], ["send_text"])
                self.assertEqual(out1.payloads[0].text, "hi from fake")

                out2 = await engine.get_reply(env)
                self.assertEqual(out1.session_id, out2.session_id)
                sm.close()

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

