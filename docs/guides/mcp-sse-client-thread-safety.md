# MCP SSE Client Thread Safety

## Summary

`openagentic_sdk.mcp.sse_client.SseMcpClient` uses two threads:

- The asyncio event loop thread (creates requests and awaits responses).
- A background reader thread (reads SSE messages and dispatches responses).

Both threads touch the `_pending` map (request id → `Future`), so it must be synchronized.

## Root Cause

`_pending` was accessed from multiple threads without a lock:

- `_request()` added new futures from the event loop thread.
- `_dispatch()` popped futures from the reader thread via `loop.call_soon_threadsafe`.
- The reader exception path iterated + cleared `_pending` directly from the reader thread.

This could race and lose pending futures or leave them unresolved.

## Fix

- Added `_pending_lock` to guard `_pending`.
- Wrapped all `_pending` reads/writes/clears in `with self._pending_lock:`.
- Kept future completion on the event loop thread via `call_soon_threadsafe`.

## Guarantees

- `_pending` modifications are serialized across threads.
- Reader failures will not silently drop pending futures without resolving them.

