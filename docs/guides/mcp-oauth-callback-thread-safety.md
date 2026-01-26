# MCP OAuth Callback Server: Thread Safety

`openagentic_sdk.mcp.oauth_callback.OAuthCallbackServer` runs an `http.server` handler on a background thread and resolves an asyncio `Future` back on the event loop.

## Issue

The `_pending` map (state → Future) was accessed from both threads without synchronization, which can lead to racey behavior (lost updates, inconsistent reads, and rare crashes).

## Fix

- Added a `_pending_lock` and guarded all `_pending` mutations/reads.
- Factored callback parsing + resolution into `OAuthCallbackServer._handle_callback_path()` so it can be unit-tested without binding a real socket.

## Verification

- `python -m unittest -q tests.test_mcp_oauth_callback_pending_thread_safety`

