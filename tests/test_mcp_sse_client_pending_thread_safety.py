import asyncio
import unittest


class _HeldFlag:
    def __init__(self) -> None:
        self.held = False


class _LockSpy:
    def __init__(self, flag: _HeldFlag) -> None:
        self._flag = flag

    def __enter__(self):  # noqa: ANN001
        self._flag.held = True
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
        self._flag.held = False
        return False


class _GuardedPending:
    def __init__(self, flag: _HeldFlag) -> None:
        self._flag = flag
        self._d: dict[int, asyncio.Future[dict]] = {}

    def _check(self) -> None:
        if not self._flag.held:
            raise AssertionError("_pending accessed without holding _pending_lock")

    def __setitem__(self, key: int, value):  # noqa: ANN001
        self._check()
        self._d[key] = value

    def pop(self, key: int, default=None):  # noqa: ANN001
        self._check()
        return self._d.pop(key, default)

    def items(self):  # noqa: ANN001
        self._check()
        return self._d.items()

    def clear(self) -> None:
        self._check()
        self._d.clear()


class TestSseMcpClientPendingThreadSafety(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_uses_pending_lock(self) -> None:
        from openagentic_sdk.mcp.sse_client import SseMcpClient

        c = SseMcpClient(base_url="http://example.invalid")
        flag = _HeldFlag()
        c._pending_lock = _LockSpy(flag)  # type: ignore[attr-defined]
        c._pending = _GuardedPending(flag)  # type: ignore[assignment]

        fut: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        with c._pending_lock:  # type: ignore[attr-defined]
            c._pending[1] = fut  # type: ignore[index]

        c._dispatch({"id": 1, "result": {}})
        await asyncio.sleep(0)
        self.assertTrue(fut.done())

