# Clawdbot Parity v1 (Gateway + Channels) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Add a Clawdbot-style resident Gateway + channel plugin architecture to this repo without modifying `openagentic_sdk` core runtime.

**Architecture:** Introduce `openagentic_gateway` as a new top-level package. It runs a long-lived HTTP+SSE control plane, manages channels (plugins + accounts), routes inbound envelopes to agent sessions, and uses `openagentic_sdk` as an “AgentCore” (preferably via sidecar HTTP proxy for maximum protocol reuse).

**Tech Stack:** Python 3.11+, stdlib `http.server` + `asyncio` (v1), `unittest`, optional SQLite for session mapping.

## Task 0: Create package skeleton

**Files:**
- Create: `openagentic_gateway/__init__.py`
- Create: `openagentic_gateway/config.py`
- Create: `openagentic_gateway/server.py`
- Test: `tests/test_gateway_health.py`

**Step 1: Write the failing test (red)**

`tests/test_gateway_health.py`:

- start gateway on an ephemeral port
- `GET /health` returns 200 and JSON with `ok: true`

**Step 2: Run test to verify it fails**

Run: `python -m unittest -q tests.test_gateway_health`  
Expected: FAIL (module/path not found or 404)

**Step 3: Minimal implementation (green)**

- Implement a minimal `GatewayServer` that starts and serves `/health`.

**Step 4: Run test to verify it passes**

Run: `python -m unittest -q tests.test_gateway_health`  
Expected: PASS

## Task 1: Add Gateway auth middleware (operator token)

**Files:**
- Modify: `openagentic_gateway/server.py`
- Create: `openagentic_gateway/auth.py`
- Test: `tests/test_gateway_auth.py`

**TDD steps**

1) Red: unauthenticated request to `/v1/gateway/status` returns 401
2) Green: add bearer token parsing and allowlist config
3) Refactor: ensure `/health` stays public (dev-friendly)

## Task 2: Add Gateway SSE event bus

**Files:**
- Modify: `openagentic_gateway/server.py`
- Create: `openagentic_gateway/events.py`
- Test: `tests/test_gateway_sse.py`

**TDD steps**

1) Red: subscribe to `/v1/events` receives `gateway.connected`
2) Green: implement SSE loop + heartbeat

## Task 3: Add Channel types + registry

**Files:**
- Create: `openagentic_gateway/channels/types.py`
- Create: `openagentic_gateway/channels/registry.py`
- Test: `tests/test_channels_registry.py`

**TDD steps**

1) Red: registry ordering and alias resolution
2) Green: implement registry and `get_channel_plugin()`

## Task 4: Implement ChannelManager

**Files:**
- Create: `openagentic_gateway/channels/manager.py`
- Test: `tests/test_channel_manager.py`

**TDD steps**

1) Red: start account calls plugin once and sets snapshot `running=True`
2) Green: implement start/stop and status updates
3) Edge: failing plugin updates `last_error` but server stays up

## Task 5: Implement routing + session mapping store

**Files:**
- Create: `openagentic_gateway/routing/resolve_route.py`
- Create: `openagentic_gateway/sessions/session_map.py`
- Test: `tests/test_routing_resolve_route.py`
- Test: `tests/test_session_map_sqlite.py`

**TDD steps**

1) Red: route keys are deterministic for dm vs group
2) Green: implement `resolve_route()`
3) Red: mapping store persists across restarts
4) Green: implement SQLite-backed `SessionMap`

## Task 6: Implement AgentCore adapter (sidecar mode)

**Files:**
- Create: `openagentic_gateway/agentcore/sidecar.py`
- Create: `openagentic_gateway/agentcore/client.py`
- Test: `tests/test_agentcore_sidecar_proxy.py`

**TDD steps**

1) Red: gateway can start AgentCore on loopback and query `/health`
2) Green: start `OpenAgenticHttpServer` on a thread and expose its port
3) Red: proxy `/permission` list returns same JSON as AgentCore
4) Green: implement proxy routing

## Task 7: Implement ReplyEngine (envelope → prompt → payloads)

**Files:**
- Create: `openagentic_gateway/reply/envelope.py`
- Create: `openagentic_gateway/reply/engine.py`
- Test: `tests/test_reply_prompt_rendering.py`
- Test: `tests/test_reply_end_to_end_fake_provider.py`

**TDD steps**

1) Red: envelope renders to prompt containing channel + peer info
2) Green: implement prompt rendering
3) Red: end-to-end: inbound → agent stub → outbound payload
4) Green: implement engine orchestration

## Task 8: Wire webhook ingress via a “test channel” plugin

**Files:**
- Create: `openagentic_gateway/channels/builtins/test_channel.py`
- Modify: `openagentic_gateway/server.py`
- Test: `tests/test_gateway_webhook_inbound.py`

**TDD steps**

1) Red: POST `/v1/chat/inbound` triggers ReplyEngine and yields outbound payloads
2) Green: implement endpoint and plugin send stub

## Task 9: Add Telegram webhook connector (first real channel)

**Files:**
- Create: `openagentic_gateway/channels/builtins/telegram_webhook.py`
- Test: `tests/test_telegram_webhook_contract.py`

**TDD steps**

1) Red: Telegram update payload normalizes to `InboundEnvelope`
2) Green: implement normalization + response mapping

## Task 10: Documentation + examples

**Files:**
- Create: `docs/guides/gateway-quickstart.md`
- Create: `example/90_gateway_telegram_webhook.py`

**TDD**

- Run the contract tests and a smoke run of the example with env-gated network disabled.

## Verification (Red/Green Light)

For each task:

- Red: targeted `python -m unittest -q tests.<module>`
- Green: same command passes
- Then run: `python -m unittest -q` (full suite) once per milestone

