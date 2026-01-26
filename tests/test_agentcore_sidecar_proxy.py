import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen


class TestAgentCoreSidecarProxy(unittest.TestCase):
    def test_gateway_proxies_permission_list_from_agentcore(self) -> None:
        from openagentic_sdk.options import OpenAgenticOptions
        from openagentic_sdk.permissions.gate import PermissionGate
        from openagentic_sdk.providers.openai_compatible import OpenAICompatibleProvider
        from openagentic_sdk.sessions.store import FileSessionStore

        from openagentic_gateway.agentcore.sidecar import AgentCoreSidecar
        from openagentic_gateway.server import GatewayServer

        os.environ.pop("OA_SERVER_TOKEN", None)
        os.environ.pop("OPENCODE_SERVER_PASSWORD", None)
        os.environ.pop("OPENCODE_SERVER_USERNAME", None)

        with tempfile.TemporaryDirectory() as td:
            store = FileSessionStore(root_dir=Path(td))
            opts = OpenAgenticOptions(
                provider=OpenAICompatibleProvider(base_url="https://example.invalid"),
                model="gpt-5.2",
                api_key=None,
                permission_gate=PermissionGate(permission_mode="deny"),
                session_store=store,
                setting_sources=[],
            )

            sidecar = AgentCoreSidecar(options=opts, host="127.0.0.1", port=0)
            agent_addr = sidecar.start()
            try:
                gw = GatewayServer(host="127.0.0.1", port=0, agentcore_url=f"http://{agent_addr.host}:{agent_addr.port}")
                gw_addr = gw.start()
                try:
                    with urlopen(f"http://{agent_addr.host}:{agent_addr.port}/permission", timeout=2.0) as resp1:  # noqa: S310
                        direct = json.loads(resp1.read().decode("utf-8"))
                    with urlopen(f"http://{gw_addr.host}:{gw_addr.port}/permission", timeout=2.0) as resp2:  # noqa: S310
                        proxied = json.loads(resp2.read().decode("utf-8"))
                    self.assertEqual(direct, proxied)
                    self.assertEqual(direct, [])
                finally:
                    gw.close()
            finally:
                sidecar.close()


if __name__ == "__main__":
    unittest.main()

