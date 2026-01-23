import io
import json
import unittest
from unittest import mock


class _DummyResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    def read(self) -> bytes:
        return self._body


class _DummyStreamResponse:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)
        self.closed = False

    def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)

    def close(self) -> None:
        self.closed = True


class TestOpenAICompatibleRetry(unittest.TestCase):
    def test_default_transport_retries_502(self) -> None:
        import urllib.error
        import urllib.request

        from openagentic_sdk.providers import openai_compatible as mod

        http_err = urllib.error.HTTPError(
            url="https://x/chat/completions",
            code=502,
            msg="Bad Gateway",
            hdrs={},
            fp=io.BytesIO(b"error code: 502"),
        )

        ok_body = json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        with mock.patch.object(urllib.request, "urlopen", side_effect=[http_err, _DummyResponse(ok_body)]) as m_open, mock.patch(
            "time.sleep"
        ) as m_sleep:
            obj = mod._default_transport(  # noqa: SLF001
                "https://x/chat/completions",
                {"content-type": "application/json"},
                {"model": "m", "messages": []},
                timeout_s=1.0,
                max_retries=1,
                retry_backoff_s=0.0,
            )

        self.assertEqual(m_open.call_count, 2)
        self.assertEqual(m_sleep.call_count, 1)
        self.assertEqual(obj["choices"][0]["message"]["content"], "ok")

    def test_default_stream_transport_retries_502(self) -> None:
        import urllib.error
        import urllib.request

        from openagentic_sdk.providers import openai_compatible as mod

        http_err = urllib.error.HTTPError(
            url="https://x/chat/completions",
            code=502,
            msg="Bad Gateway",
            hdrs={},
            fp=io.BytesIO(b"error code: 502"),
        )
        stream_resp = _DummyStreamResponse([b"data: {\"choices\": []}\n\n", b"data: [DONE]\n\n"])

        with mock.patch.object(urllib.request, "urlopen", side_effect=[http_err, stream_resp]) as m_open, mock.patch(
            "time.sleep"
        ) as m_sleep:
            chunks = mod._default_stream_transport(  # noqa: SLF001
                "https://x/chat/completions",
                {"content-type": "application/json"},
                {"model": "m", "messages": [], "stream": True},
                timeout_s=1.0,
                max_retries=1,
                retry_backoff_s=0.0,
            )
            first = next(iter(chunks))

        self.assertEqual(m_open.call_count, 2)
        self.assertEqual(m_sleep.call_count, 1)
        self.assertTrue(first.startswith(b"data:"))


if __name__ == "__main__":
    unittest.main()

