# Clawdbot Parity v1 — Nodes/Devices (Optional Capability Surface)

## Analysis (Clawdbot)

Clawdbot models “nodes/devices” as paired capability providers:

- pairing methods and scopes
- node invoke requests/results/events

References:

- `src/gateway/server-methods.ts` (`NODE_ROLE_METHODS`, pairing methods)
- `src/gateway/server-methods-list.ts` (node.* methods)

## v1 Position

This is explicitly **optional** for v1 parity. We document it now so the design doesn’t block future expansion.

## Design Sketch

Gateway supports:

- node registration: node connects with role `node` token
- capability manifest: `node.describe`
- invocation: `node.invoke` (operator triggers; node executes)
- results/events: `node.invoke.result`, `node.event`

Transport options:

- HTTP long-polling + SSE (reuse streaming model)
- WebSocket (later)

## Plan (Deferred)

1) Define protocol message shapes (JSON).
2) Implement auth role `node`.
3) Implement minimal node emulator for integration tests.

## TDD

Only start when we have Gateway auth + events streaming solid.

## Acceptance Checklist (When Implemented)

- Node cannot call operator-only endpoints.
- Operator can invoke a node capability and receive a result.

