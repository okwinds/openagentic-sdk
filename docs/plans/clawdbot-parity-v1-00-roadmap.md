# Clawdbot Parity v1 — Roadmap (Milestones)

This is the “what order do we build in” roadmap. Detailed task breakdowns live in `docs/plans/clawdbot-parity-v1-12-implementation-plan.md`.

## Milestone 0 — Scaffolding + boundaries

- Add a new top-level package for the control plane (proposed name: `openagentic_gateway`).
- Define the hard boundary:
  - `openagentic_sdk`: agent runtime library (unchanged)
  - `openagentic_gateway`: long-running server + channel orchestration (new)

**Exit criteria**

- You can import `openagentic_gateway` from tests.
- A `GatewayConfig` can be loaded from disk (even if minimal).
- A `GatewayServer` starts and answers `GET /health`.

## Milestone 1 — “AgentCore” integration (reuse existing protocol)

We intentionally reuse `openagentic_sdk.server.http_server.OpenAgenticHttpServer` as the AgentCore process/server surface (OpenCode parity endpoints + permission/question queues + SSE event bus).

Two acceptable integration shapes:

- A) **In-process**: Gateway imports AgentRuntime directly and provides an operator approval bridge.
- B) **Sidecar** (preferred for reuse): Gateway starts an internal AgentCore HTTP server on loopback and **proxies** key endpoints (permissions, sessions, streaming).

**Exit criteria**

- Gateway can trigger an AgentCore session run (async) with a known `session_id`.
- Tool approval requests can be surfaced via operator endpoints (proxy OK).

## Milestone 2 — Routing + session mapping store

Align with Clawdbot’s idea of `(channel/account/peer/guild/team) → agentId + sessionKey`.

**Exit criteria**

- A deterministic `session_key` scheme exists.
- A persistent mapping store (SQLite or JSONL) can resolve:
  - (channel, account_id, peer_id) → agent session_id
  - support “main session” per agent (optional)

## Milestone 3 — Channel plugin contract + ChannelManager

Align with Clawdbot:

- Channel plugins declare metadata + capabilities + adapters.
- ChannelManager owns multi-account lifecycle and status snapshots.

**Exit criteria**

- At least one “toy channel” plugin exists (in-memory / test channel).
- ChannelManager can start/stop accounts and produce a snapshot.

## Milestone 4 — Reply engine (message in → payloads out)

We need a unified inbound envelope and an outbound payload model.

**Exit criteria**

- Given an inbound message envelope, we can:
  - resolve route (agent + session)
  - produce an agent prompt (text + attachments refs)
  - execute agent via AgentCore
  - produce outbound payload(s) suitable for a channel adapter

## Milestone 5 — First real connector (Telegram webhook)

Telegram is the first pragmatic connector because it can be webhook-based (no long-lived WS requirement).

**Exit criteria**

- Gateway exposes a Telegram webhook endpoint.
- A test harness replays webhook payloads and asserts outbound messages.

## Milestone 6 — Expand channels + optional features

- Slack (socket mode or events API)
- Discord (gateway WS)
- “Nodes/devices” pairing and remote capabilities (optional, later)

