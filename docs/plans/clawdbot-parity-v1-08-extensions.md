# Clawdbot Parity v1 — Extensions: Plugins, Tools, and Gateway Hooks

## Analysis (Clawdbot)

Clawdbot supports extensions that can:

- register gateway methods
- register channel plugins
- add tools/capabilities to agent runtime

Reference: `src/plugins/loader.ts`, `src/plugins/registry.ts`

## Current State (openagentic-sdk)

SDK already supports plugins (tools + hooks):

- Python plugins: `openagentic_sdk/plugins.py`
- JS/TS tool plugins (bun runner): `openagentic_sdk/js_plugins.py`

This is valuable; we should reuse it rather than rebuilding tool/plugin concepts in the Gateway.

## Design

We split extension points:

1) **Agent extensions** (SDK-owned):
   - tools and hooks loaded via existing SDK plugin specs
2) **Gateway extensions** (Gateway-owned):
   - channel plugins
   - gateway HTTP routes (webhooks, operator endpoints)
   - optional gateway event hooks

### Gateway plugin contract (v1)

```py
class GatewayPlugin(Protocol):
    def register(self, registry: GatewayRegistry) -> None: ...
```

Where `GatewayRegistry` can register:

- channel plugins
- additional http handlers (path → callable)
- gateway event subscribers

## Plan (Implementation Outline)

1) Define `GatewayRegistry` + `GatewayPlugin` interfaces.
2) Implement plugin loading by import spec:
   - `module:obj` or plain module with `register(registry)`
3) Add tests for:
   - plugin discovery and deterministic ordering
   - error isolation (plugin failure does not crash gateway)
4) Wire SDK plugin specs through to AgentCore options (no SDK changes):
   - Gateway config includes `agent_plugins: [...]` passed into SDK options.

## TDD

Start with plugin loading unit tests using temp modules under `tests/fixtures/`.

## Acceptance Checklist

- A gateway plugin can register a channel plugin and it becomes available via `GET /v1/channels`.
- A gateway plugin can add an HTTP route.
- SDK tool plugins remain configured via SDK mechanisms (not duplicated).

