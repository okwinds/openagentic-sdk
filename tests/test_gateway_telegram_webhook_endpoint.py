import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request, urlopen


class _FakeResponsesProvider:
    name = "fake"

    async def complete(self, *, model, input, **kwargs):  # noqa: A002
        from openagentic_sdk.providers.base import ModelOutput

        return ModelOutput(assistant_text="pong", tool_calls=(), provider_metadata={"protocol": "responses"})


class TestGatewayTelegramWebhookEndpoint(unittest.TestCase):
    def test_post_telegram_webhook_runs_reply_engine(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.permissions.gate import PermissionGate
        from openagentic_sdk.sessions.store import FileSessionStore

        from openagentic_gateway.reply.engine import ReplyEngine
        from openagentic_gateway.server import GatewayServer
        from openagentic_gateway.sessions.session_map import SessionMap

        os.environ.pop("OA_GATEWAY_TOKEN", None)

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
            gw = GatewayServer(host="127.0.0.1", port=0, reply_engine=engine)
            addr = gw.start()
            try:
                update = {
                    "update_id": 1,
                    "message": {"message_id": 10, "chat": {"id": 123, "type": "private"}, "text": "hi"},
                }
                req = Request(
                    f"http://{addr.host}:{addr.port}/v1/webhooks/telegram/acc1",
                    data=json.dumps(update).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=5.0) as resp:  # noqa: S310
                    self.assertEqual(resp.status, 200)
                    obj = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(obj["payloads"][0]["text"], "pong")
            finally:
                gw.close()
                sm.close()


if __name__ == "__main__":
    unittest.main()

