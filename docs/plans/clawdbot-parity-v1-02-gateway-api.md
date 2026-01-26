# Clawdbot Parity v1 — Gateway API (HTTP + Streaming)

## Analysis (Clawdbot)

Clawdbot exposes a method-based RPC surface (WS) with auth/scopes:

- Method catalog: `src/gateway/server-methods-list.ts`
- Auth enforcement: `src/gateway/server-methods.ts`

The Gateway is also an HTTP server (web hooks, optional OpenAI-compatible endpoints).

## Current State (openagentic-sdk)

`openagentic_sdk/server/http_server.py` already provides:

- `GET /health` and `GET /global/health`
- `GET /event` (SSE bus)
- `GET /provider` and `/provider/auth` (parity endpoints)
- `/session/*` endpoints (create, message, prompt_async, abort, fork, revert, etc.)
- `/permission/*` and `/question/*` queue endpoints used by a browser/extension to approve tools

This is a useful “AgentCore HTTP protocol” that we can reuse.

## Design Goal

Expose a Gateway HTTP surface that:

- Is stable for operator clients (CLI/UI)
- Supports channel webhooks
- Can proxy (or embed) AgentCore endpoints without changing SDK internals

## Proposed API Surfaces

### 1) Gateway Operator Surface (new)

Minimal v1 endpoints:

- `GET /health`
- `GET /v1/gateway/status`
- `GET /v1/channels` (list plugins + account statuses)
- `POST /v1/channels/{channel}/start` (optional `account_id`)
- `POST /v1/channels/{channel}/stop`
- `POST /v1/chat/inbound` (for connectors running out-of-process)
- `GET /v1/events` (SSE stream: gateway events + proxied agent events)

### 2) Channel Webhook Surface (new; per channel)

Example (Telegram):

- `POST /v1/webhooks/telegram/{account_id}`

### 3) AgentCore Surface (reused via proxy)

Gateway proxies to an internal AgentCore server:

- `/session/*`
- `/permission/*`
- `/question/*`
- `/event` (SSE)

This lets us reuse the existing protocol and UI affordances.

## Streaming Model

We align with the repo’s existing SSE style:

- `GET /v1/events` is SSE.
- Event types:
  - `gateway.connected`, `gateway.heartbeat`
  - `channels.status`, `channel.account.started/stopped/error`
  - `agent.session.event` (proxied from AgentCore `session.event`)

## Error Model

Use JSON errors with stable fields:

```json
{ "error": { "code": "invalid_request", "message": "..." } }
```

## Plan (Implementation Outline)

1) Contract tests for the Gateway surface (no AgentCore yet).
2) Implement `GET /health` and `GET /v1/gateway/status`.
3) Add SSE `/v1/events` (queue + heartbeat).
4) Add AgentCore sidecar and proxy routes for `/session/*`, `/permission/*`, `/question/*`, `/event`.
5) Add webhook routes behind channel plugins.

## TDD

- Unit tests: request parsing and auth decision logic.
- Contract tests: start server on ephemeral port and assert JSON + status codes.
- Integration: run AgentCore sidecar in tests and assert proxy correctness.

## Acceptance Checklist

- Gateway can serve operator endpoints independently.
- Gateway can proxy AgentCore endpoints without modifying SDK.
- A client can subscribe to SSE and see both gateway + agent events.

