import json
import unittest
from urllib.request import urlopen


class TestGatewayHealth(unittest.TestCase):
    def test_health_endpoint_returns_ok_true(self) -> None:
        from openagentic_gateway.server import GatewayServer

        gw = GatewayServer(host="127.0.0.1", port=0)
        addr = gw.start()
        try:
            with urlopen(f"http://{addr.host}:{addr.port}/health", timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                obj = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(obj, {"ok": True})
        finally:
            gw.close()


if __name__ == "__main__":
    unittest.main()

