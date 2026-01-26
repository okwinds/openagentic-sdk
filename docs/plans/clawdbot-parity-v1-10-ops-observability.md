# Clawdbot Parity v1 — Ops + Observability

## Goals

- Gateway is long-running; it must be diagnosable.
- Failures in one channel must not crash the entire process.

## Design (v1)

### Logging

- Structured logs to stdout by default.
- Per-channel logger names (`channel.telegram`, etc.).
- Correlation ids:
  - `request_id` for webhook requests
  - `session_id` for agent runs

### Health

- `GET /health` returns:
  - `ok`
  - `uptime_s`
  - `channels_running`
  - `agentcore_mode` (in-process vs sidecar)

### Metrics (optional v1)

Keep minimal:

- counters: inbound messages, outbound sends, agent runs, tool approvals requested/approved/denied

## Plan (Implementation Outline)

1) Contract tests for `GET /health`.
2) Add structured logging wrapper for gateway modules.
3) Add per-channel logging context to ChannelManager and ReplyEngine.
4) Add a minimal metrics store (in-memory) and expose in `/v1/gateway/status`.

## TDD

Test health JSON shape and that channel failures are reflected in status.

## Acceptance Checklist

- A channel crash is surfaced in status and logs but does not bring down gateway.
- Health endpoint is fast and always available.

