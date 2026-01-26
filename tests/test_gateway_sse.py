import json
import os
import unittest
from urllib.request import urlopen


def _read_until_double_newline(resp, *, limit: int = 10_000) -> bytes:
    buf = bytearray()
    while len(buf) < limit:
        b = resp.read(1)
        if not b:
            break
        buf.extend(b)
        if buf.endswith(b"\n\n"):
            break
    return bytes(buf)


class TestGatewaySse(unittest.TestCase):
    def test_events_stream_emits_gateway_connected(self) -> None:
        from openagentic_gateway.server import GatewayServer

        os.environ.pop("OA_GATEWAY_TOKEN", None)
        gw = GatewayServer(host="127.0.0.1", port=0)
        addr = gw.start()
        try:
            with urlopen(f"http://{addr.host}:{addr.port}/v1/events", timeout=2.0) as resp:  # noqa: S310
                chunk = _read_until_double_newline(resp)
                text = chunk.decode("utf-8", errors="replace")
                self.assertIn("data:", text)
                line = next((ln for ln in text.splitlines() if ln.startswith("data: ")), "")
                payload = line[len("data: ") :].strip()
                obj = json.loads(payload)
                self.assertEqual(obj.get("type"), "gateway.connected")
        finally:
            gw.close()


if __name__ == "__main__":
    unittest.main()

