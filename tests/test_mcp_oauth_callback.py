import asyncio
import urllib.error
import urllib.request
import unittest


class TestMcpOauthCallback(unittest.IsolatedAsyncioTestCase):
    async def test_wait_for_callback_resolves_code(self) -> None:
        from openagentic_sdk.mcp.oauth_callback import OAuthCallbackServer

        srv = OAuthCallbackServer(port=0)
        fut: asyncio.Task[str] | None = None
        await srv.start()
        try:
            state = "s1"
            fut = asyncio.create_task(srv.wait_for_callback(state, timeout_s=2.0))

            # Ensure the callback waiter is registered before triggering the GET.
            await asyncio.sleep(0)

            url = f"{srv.redirect_uri}?code=c1&state={state}"
            # Trigger callback.
            def _hit() -> None:
                with urllib.request.urlopen(url) as _resp:  # noqa: S310
                    _resp.read(0)

            await asyncio.to_thread(_hit)
            code = await fut
            self.assertEqual(code, "c1")
        finally:
            if fut is not None and not fut.done():
                fut.cancel()
            await srv.close()

    async def test_missing_state_returns_400(self) -> None:
        from openagentic_sdk.mcp.oauth_callback import OAuthCallbackServer

        srv = OAuthCallbackServer(port=0)
        await srv.start()
        try:
            url = f"{srv.redirect_uri}?code=c1"
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                await asyncio.to_thread(urllib.request.urlopen, url)
            self.assertEqual(ctx.exception.code, 400)
            try:
                ctx.exception.close()
            except Exception:
                pass
        finally:
            await srv.close()

    async def test_unknown_state_returns_400(self) -> None:
        from openagentic_sdk.mcp.oauth_callback import OAuthCallbackServer

        srv = OAuthCallbackServer(port=0)
        await srv.start()
        try:
            url = f"{srv.redirect_uri}?code=c1&state=missing"
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                await asyncio.to_thread(urllib.request.urlopen, url)
            self.assertEqual(ctx.exception.code, 400)
            try:
                ctx.exception.close()
            except Exception:
                pass
        finally:
            await srv.close()


if __name__ == "__main__":
    unittest.main()
