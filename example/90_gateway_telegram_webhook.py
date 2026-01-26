import json
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from openagentic_gateway.reply.engine import ReplyEngine
from openagentic_gateway.server import GatewayServer
from openagentic_gateway.sessions.session_map import SessionMap
from openagentic_sdk.options import OpenAgenticOptions
from openagentic_sdk.permissions.gate import PermissionGate
from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
from openagentic_sdk.sessions.store import FileSessionStore


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        store = FileSessionStore(root_dir=root / "sessions")
        sm = SessionMap(path=str(root / "session_map.sqlite3"))

        opts = OpenAgenticOptions(
            provider=OpenAICompatibleProvider(base_url="https://example.invalid"),
            model="gpt-5.2",
            api_key=None,
            permission_gate=PermissionGate(permission_mode="deny"),
            session_store=store,
            setting_sources=[],
        )
        engine = ReplyEngine(options=opts, session_map=sm, agent_id="agent1")

        gw = GatewayServer(host="127.0.0.1", port=0, reply_engine=engine)
        addr = gw.start()
        try:
            print(f"Gateway running at http://{addr.host}:{addr.port}")

            update = {
                "update_id": 1,
                "message": {"message_id": 10, "chat": {"id": 123, "type": "private"}, "text": "hello"},
            }
            req = Request(
                f"http://{addr.host}:{addr.port}/v1/webhooks/telegram/default",
                data=json.dumps(update).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5.0) as resp:  # noqa: S310
                print(resp.status, resp.read().decode("utf-8"))
        finally:
            gw.close()
            sm.close()


if __name__ == "__main__":
    main()

