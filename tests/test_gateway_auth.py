import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class TestGatewayAuth(unittest.TestCase):
    def test_status_requires_bearer_token(self) -> None:
        from openagentic_gateway.server import GatewayServer

        os.environ["OA_GATEWAY_TOKEN"] = "secret"
        gw = GatewayServer(host="127.0.0.1", port=0)
        addr = gw.start()
        try:
            req = Request(f"http://{addr.host}:{addr.port}/v1/gateway/status")
            with self.assertRaises(HTTPError) as cm:
                urlopen(req, timeout=2.0)  # noqa: S310
            self.assertEqual(cm.exception.code, 401)

            req2 = Request(f"http://{addr.host}:{addr.port}/v1/gateway/status")
            req2.add_header("Authorization", "Bearer secret")
            with urlopen(req2, timeout=2.0) as resp:  # noqa: S310
                self.assertEqual(resp.status, 200)
                obj = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(obj.get("ok"), True)
        finally:
            gw.close()


if __name__ == "__main__":
    unittest.main()

