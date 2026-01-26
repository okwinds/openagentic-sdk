import asyncio
import unittest


class _GuardDict(dict):
    def __init__(self, lock: asyncio.Lock | object, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
        super().__init__(*args, **kwargs)
        self._lock = lock

    def _assert_locked(self) -> None:
        locked = getattr(self._lock, "locked", None)
        if callable(locked):
            assert locked(), "expected pending lock to be held"

    def __contains__(self, key: object) -> bool:  # noqa: D105
        self._assert_locked()
        return super().__contains__(key)

    def __setitem__(self, key, value) -> None:  # noqa: ANN001,D105
        self._assert_locked()
        return super().__setitem__(key, value)

    def pop(self, key, default=None):  # noqa: ANN001,D102
        self._assert_locked()
        return super().pop(key, default)

    def items(self):  # noqa: D102
        self._assert_locked()
        return super().items()

    def clear(self) -> None:  # noqa: D102
        self._assert_locked()
        super().clear()


class TestMcpOauthCallbackPendingThreadSafety(unittest.IsolatedAsyncioTestCase):
    async def test_pending_map_is_guarded_by_lock(self) -> None:
        from openagentic_sdk.mcp.oauth_callback import OAuthCallbackServer

        server = OAuthCallbackServer()
        server._loop = asyncio.get_running_loop()  # noqa: SLF001
        server._pending = _GuardDict(server._pending_lock)  # noqa: SLF001

        state = "s1"
        fut = asyncio.get_running_loop().create_future()
        with server._pending_lock:  # noqa: SLF001
            server._pending[state] = fut  # noqa: SLF001

        code, body = server._handle_callback_path(f"{server.path}?state={state}&code=c1")  # noqa: SLF001
        self.assertEqual(code, 200)
        self.assertIn(b"OAuth complete", body)

        await asyncio.sleep(0)
        self.assertTrue(fut.done())
        self.assertEqual(fut.result(), "c1")

    async def test_close_fails_pending_waiters_under_lock(self) -> None:
        from openagentic_sdk.mcp.oauth_callback import OAuthCallbackServer

        server = OAuthCallbackServer()
        server._loop = asyncio.get_running_loop()  # noqa: SLF001
        server._pending = _GuardDict(server._pending_lock)  # noqa: SLF001

        fut = asyncio.get_running_loop().create_future()
        with server._pending_lock:  # noqa: SLF001
            server._pending["s2"] = fut  # noqa: SLF001

        await server.close()
        self.assertTrue(fut.done())
        with self.assertRaises(RuntimeError):
            _ = fut.result()


if __name__ == "__main__":
    unittest.main()

