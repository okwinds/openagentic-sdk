# Clawdbot Parity v1 — Channel Plugin Contract (Python)

## Analysis (Clawdbot)

Clawdbot’s channel plugin contract is extensive; the key pieces for v1 parity:

- identity/meta + capabilities
- config and account enumeration
- gateway lifecycle hooks (`startAccount`, `stopAccount`)
- inbound/outbound adapters

Reference: `src/channels/plugins/types.plugin.ts`

## Design Principle

We build a **minimal, extensible** Python contract that can grow, but we don’t copy every adapter on day one.

## Proposed Python Interfaces

### Core types

- `ChannelId`: `str`
- `AccountId`: `str`
- `ChannelPeer`: dm/group identity
- `InboundEnvelope`: normalized inbound message
- `OutboundPayload`: normalized outbound action(s)

### Plugin contract (v1)

```py
class ChannelPlugin(Protocol):
    id: str
    meta: ChannelMeta
    capabilities: ChannelCapabilities

    def list_account_ids(self, cfg: GatewayConfig) -> list[str]: ...
    def resolve_account(self, cfg: GatewayConfig, account_id: str) -> Any: ...
    async def is_enabled(self, account: Any, cfg: GatewayConfig) -> bool: ...
    async def is_configured(self, account: Any, cfg: GatewayConfig) -> bool: ...

    async def start_account(self, ctx: ChannelStartContext) -> None: ...
    async def stop_account(self, ctx: ChannelStopContext) -> None: ...

    async def send(self, ctx: ChannelSendContext, payload: OutboundPayload) -> None: ...
```

We intentionally keep “inbound receiving” flexible:

- webhook-based channels register HTTP routes
- polling-based channels schedule background tasks
- gateway-ws-based channels spawn background loops

## Registry + Discovery

Align with repo style:

- Explicit registry module with stable ordering (like `clawdbot/src/channels/registry.ts`).
- Support third-party plugins via entrypoints or config-based import specs.

## Plan (Implementation Outline)

1) Define types in `openagentic_gateway/channels/types.py`.
2) Implement a registry in `openagentic_gateway/channels/registry.py`.
3) Implement plugin loader:
   - built-ins: import by module path
   - external: optional Python entrypoints later
4) Add a “test channel” plugin:
   - in-memory inbox/outbox for integration tests

## TDD

- Unit tests:
  - registry ordering and lookup
  - plugin loader behavior (invalid module, missing attrs)
- Integration test:
  - start ChannelManager with test plugin and assert lifecycle calls

## Acceptance Checklist

- A channel plugin can be started/stopped per account.
- The plugin can emit inbound messages into the ReplyEngine.
- The plugin can receive outbound payloads and “send” them (test channel asserts).

