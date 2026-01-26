# Clawdbot Parity v1 — ChannelManager (Multi-account Lifecycle)

## Analysis (Clawdbot)

`createChannelManager()` is the unifying lifecycle layer:

- starts/stops channel plugin accounts
- tracks per-account runtime status (`running`, `connected`, `lastError`, timestamps)
- yields snapshots for UI

Reference: `src/gateway/server-channels.ts`

## Design

Implement `ChannelManager` in the Gateway layer with:

- per-channel store:
  - `aborts: dict[account_id, AbortController]` (Python: `asyncio.Event` or `asyncio.Task` cancel)
  - `tasks: dict[account_id, asyncio.Task]`
  - `runtimes: dict[account_id, ChannelAccountSnapshot]`

Expose:

- `start_channels()`
- `start_channel(channel_id, account_id=None)`
- `stop_channel(...)`
- `get_snapshot()`

## Status Snapshot (v1)

```json
{
  "channels": {
    "telegram": { "account_id": "default", "running": true, "last_error": null }
  },
  "channel_accounts": {
    "telegram": {
      "default": { "running": true, "last_start_at": 123, "last_error": null }
    }
  }
}
```

## Plan (Implementation Outline)

1) Unit test: starting a channel calls `plugin.start_account()` exactly once per account.
2) Unit test: stopping a channel cancels tasks and calls `plugin.stop_account()`.
3) Implement `ChannelManager` with in-memory stores.
4) Add Gateway API endpoints:
   - `POST /v1/channels/{id}/start`
   - `POST /v1/channels/{id}/stop`
   - `GET /v1/channels`

## TDD

Use a fake plugin that:

- records calls
- blocks on an `asyncio.Event()` until canceled

## Acceptance Checklist

- Multiple accounts can run concurrently under one channel.
- Failures update `last_error` without crashing the gateway.
- Snapshot is deterministic and stable.

