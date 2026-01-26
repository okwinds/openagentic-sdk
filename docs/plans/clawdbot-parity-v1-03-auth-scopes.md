# Clawdbot Parity v1 — Auth, Roles, Scopes, Approvals

## Analysis (Clawdbot)

Clawdbot uses:

- roles: `operator` vs `node` (and admin scopes)
- scoped permissions for methods (read/write/approvals/pairing)

References:

- `src/gateway/server-methods.ts` (authorizeGatewayMethod)
- `src/gateway/server-methods-list.ts` (method inventory)

## Current State (openagentic-sdk)

`openagentic_sdk/server/http_server.py` supports:

- optional auth gates:
  - Basic auth (OpenCode parity env vars)
  - bearer token (`OA_SERVER_TOKEN`)

It does **not** model roles/scopes explicitly (today).

## Design

We implement auth/scopes at the **Gateway layer** (upper package), without changing SDK:

- Role: `operator` (human control plane) vs `connector` (channel integration process) vs `node` (future)
- Scope: `read`, `write`, `approvals`, `pairing`, `admin`

### Minimal v1 auth

- Bearer token in `Authorization: Bearer <token>`
  - `OA_GATEWAY_TOKEN` for operator
  - `OA_GATEWAY_CONNECTOR_TOKEN` for connectors (optional)

### Optional v1 roles/scopes encoding

Encode scopes in config (static allowlist):

```json
{
  "tokens": [
    { "token": "…", "role": "operator", "scopes": ["admin"] },
    { "token": "…", "role": "connector", "scopes": ["write"] }
  ]
}
```

## Approvals Model (Core Principle)

Channels are untrusted inputs. Tool execution is dangerous. We align with:

- The SDK’s `PermissionGate` as the enforcement mechanism.
- The Gateway’s operator surface as the approval UI/queue.

Two integration modes:

- Sidecar mode (preferred): rely on AgentCore `/permission` + `/question` queue endpoints and proxy them.
- In-process mode: implement a PermissionGate callback that enqueues approval requests to the gateway.

## Plan (Implementation Outline)

1) Unit tests for:
   - token parsing and rejection
   - role/scope checks per route
2) Contract tests:
   - `GET /v1/gateway/status` requires operator scope
   - webhook route requires connector scope (or signed secret)
3) Implement auth middleware in `openagentic_gateway`.
4) Implement approval proxy in sidecar mode.

## TDD (Red/Green)

Start with auth unit tests and contract tests *before* adding any production code.

## Acceptance Checklist

- Operator endpoints are not reachable without auth (unless explicitly configured for dev).
- Connector endpoints are isolated from operator endpoints.
- Approvals are never silently auto-approved in production configuration.

