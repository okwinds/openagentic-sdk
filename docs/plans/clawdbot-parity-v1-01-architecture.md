# Clawdbot Parity v1 — Target Architecture (From Code + Runtime Topology)

## Analysis (Clawdbot)

Clawdbot’s key split is:

- **CLI**: user entrypoint; talks to Gateway over RPC
- **Gateway**: resident control plane; owns channels, routing, approvals, agent execution

Relevant code references (Clawdbot):

- CLI entry: `src/entry.ts`
- CLI main: `src/cli/run-main.ts`
- Gateway start: `src/gateway/server.impl.ts`
- Gateway auth/methods: `src/gateway/server-methods.ts`, `src/gateway/server-methods-list.ts`
- Channel lifecycle: `src/gateway/server-channels.ts`
- Channel plugin contract: `src/channels/plugins/types.plugin.ts`
- Reply engine entry: `src/auto-reply/reply/get-reply.ts`
- Route resolver: `src/routing/resolve-route.ts`

## Current State (openagentic-sdk)

This repo already has:

- `openagentic_sdk/runtime.py`: sessions + tool loop + permission gate + hooks/plugins
- `openagentic_sdk/server/http_server.py`: OpenCode-parity-ish HTTP surface + SSE event bus + approval/question queues
- `openagentic_cli/*`: a local CLI/TUI-ish REPL that talks to the runtime in-process

What we do *not* have yet:

- A persistent “Gateway” abstraction for multi-channel connectors and lifecycle
- A channel plugin contract and manager
- A reply engine that takes a channel envelope and returns outbound payloads

## Target Topology (v1)

Proposed logical topology (Python):

```
[oa CLI (operator)] --HTTP/SSE--> [OpenAgentic Gateway]
                                   |-- ChannelManager (per channel/account lifecycle)
                                   |-- ReplyEngine (normalize inbound → agent → payloads)
                                   |-- Routing + SessionMap (channel/account/peer → session_id)
                                   |-- Extensions (gateway plugins, channel plugins)
                                   |-- Optional: Nodes/Devices (remote capabilities)
                                   `-- AgentCore (reused openagentic-sdk)
                                          (either in-process, or sidecar HTTP server)
```

## Boundary Rules (Hard)

- `openagentic_sdk` stays focused on agent runtime primitives:
  - providers/models, tool loop, PermissionGate, session store, hooks/tools plugins
- `openagentic_gateway` is a *product surface*:
  - endpoints, auth/scopes, channel connectors, routing policy, lifecycle orchestration

## Data Flow (Inbound → Reply)

1) Channel adapter receives inbound event (message/webhook).
2) Convert to a normalized `InboundEnvelope`:
   - `channel`, `account_id`, `peer` (dm/group), `message_id`, `text`, `attachments`, `timestamp`, `raw`
3) ReplyEngine resolves `Route`:
   - `agent_id`, `session_key`, `session_id` (from SessionMap)
4) ReplyEngine calls AgentCore with `prompt` and `resume=session_id`.
5) AgentCore emits events; Gateway streams them (optional) and accumulates final text.
6) ReplyEngine maps final text to `OutboundPayload[]`.
7) Channel adapter sends payloads back to the platform.

## Plan (Execution Outline)

- Implement minimal Gateway skeleton and keep it running (Milestone 0).
- Add AgentCore sidecar mode with proxy endpoints (Milestone 1).
- Add routing + SessionMap store (Milestone 2).
- Add Channel plugins + manager (Milestone 3).
- Add ReplyEngine (Milestone 4).
- Add first real channel (Milestone 5).

## TDD (Red/Green)

For each milestone:

- Red: write failing unit/contract tests
- Green: implement minimal code
- Refactor: only with tests passing

## Acceptance Checklist

- The Gateway is a separate package/process (not “SDK mutated into an app”).
- A fake channel can deliver an inbound message and receive an outbound payload.
- Tool approval flow is mediated by operator endpoints (no auto-approve by default).

