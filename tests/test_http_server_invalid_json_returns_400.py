import io
import json
import unittest


class _FakeServer:
    def __init__(self, max_request_bytes: int = 2_000_000) -> None:
        self.max_request_bytes = max_request_bytes


class _FakeHandler:
    def __init__(self, body: bytes, *, max_request_bytes: int = 2_000_000) -> None:
        self.server = _FakeServer(max_request_bytes=max_request_bytes)
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status: int | None = None
        self.sent_headers: dict[str, str] = {}

    def send_response(self, status: int) -> None:
        self.status = int(status)

    def send_header(self, key: str, value: str) -> None:
        self.sent_headers[str(key).lower()] = str(value)

    def end_headers(self) -> None:  # noqa: D401
        return


class TestHttpServerInvalidJson(unittest.TestCase):
    def test_read_json_raises_value_error_on_invalid_json(self) -> None:
        import openagentic_sdk.server.http_server as hs

        h = _FakeHandler(b"{not-json")
        with self.assertRaises(ValueError) as ctx:
            hs._read_json(h)  # type: ignore[arg-type]
        self.assertEqual(str(ctx.exception), "invalid_json")

    def test_invalid_json_maps_to_http_400(self) -> None:
        import openagentic_sdk.server.http_server as hs

        helper = getattr(hs, "_read_json_or_write_error", None)
        self.assertIsNotNone(helper, "missing _read_json_or_write_error helper")

        h = _FakeHandler(b"{not-json")
        out = helper(h)  # type: ignore[misc]
        self.assertIsNone(out)
        self.assertEqual(h.status, 400)

        payload = json.loads(h.wfile.getvalue().decode("utf-8", errors="replace"))
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("error"), "invalid_json")

