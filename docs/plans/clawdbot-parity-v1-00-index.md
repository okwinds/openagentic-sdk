# Clawdbot Parity v1 (Gateway + Channels) — Index

Goal: bring **Clawdbot-style multi-channel ChatOps** to this repo while keeping `openagentic_sdk` “底层”稳定：渠道连接器与控制平面在**上层包/进程**实现，SDK 继续专注 agent runtime（sessions/tools/permissions/hooks/providers）。

Source of truth (Clawdbot local): `/mnt/e/development/clawdbot`

## Non-negotiables

- **Do not** modify `openagentic_sdk/*` core runtime logic for the first milestone. If a change is truly required, it must be justified by a failing test + minimal surface.
- Channels (Telegram/Slack/Discord/WhatsApp/…) are **upper-layer integrations**, not SDK primitives.
- Execution discipline is mandatory:
  - **分析 → 设计 → 落地计划 → TDD → 红绿灯 → 回顾 → 下一个任务**

## What “Parity” Means Here

We are not cloning Clawdbot line-by-line. We are aligning on these product-level behaviors:

- A **resident control plane** (“Gateway”) that:
  - owns channel account lifecycle (start/stop/status)
  - normalizes inbound messages into a unified envelope
  - routes to an agent + session
  - mediates tool approvals via an operator surface
  - returns outbound payloads back to the channel
- A **thin CLI** that connects to the Gateway (operator role), and can also run “local-only” workflows.

## Execution Policy (Waterfall + TDD Loop)

For each plan doc in this series:

1) **Analysis**: extract Clawdbot behavior (with file references)
2) **Design**: propose the equivalent in Python (components + data flow)
3) **Execution plan**: small, ordered tasks with exact file paths
4) **TDD**: write tests first (red)
5) **Implement**: minimal code to pass tests (green)
6) **Refactor**: only if needed (still green)
7) **Review + recap**: verify + document; then pick the next task

## Definition of Done (Per Feature)

- Clear boundary: SDK remains a library; Gateway/Channels live “outside”.
- Deterministic behavior: stable routing keys and stable serialization.
- Safety: tool approvals are explicit; no silent shell/network escalation.
- Tests:
  - Unit tests for routing/parsing.
  - Contract tests for Gateway HTTP surface.
  - Integration tests for end-to-end inbound→agent→outbound.

## Dependency Order (Foundational First)

1) Architecture + boundaries
2) Gateway API + Auth/Scopes
3) Session routing + mapping store
4) Channel plugin contract + channel manager
5) Reply engine (message→prompt→payload)
6) Extensions/tools wiring (reuse SDK plugins where possible)
7) Nodes/devices (optional)
8) Ops/observability
9) Testing strategy and harness hardening

## Plan Documents (v1)

- `docs/plans/clawdbot-parity-v1-00-roadmap.md`
- `docs/plans/clawdbot-parity-v1-01-architecture.md`
- `docs/plans/clawdbot-parity-v1-02-gateway-api.md`
- `docs/plans/clawdbot-parity-v1-03-auth-scopes.md`
- `docs/plans/clawdbot-parity-v1-04-channel-plugins.md`
- `docs/plans/clawdbot-parity-v1-05-channel-manager.md`
- `docs/plans/clawdbot-parity-v1-06-routing-sessions.md`
- `docs/plans/clawdbot-parity-v1-07-reply-engine.md`
- `docs/plans/clawdbot-parity-v1-08-extensions.md`
- `docs/plans/clawdbot-parity-v1-09-nodes-devices.md`
- `docs/plans/clawdbot-parity-v1-10-ops-observability.md`
- `docs/plans/clawdbot-parity-v1-11-testing-tdd.md`
- `docs/plans/clawdbot-parity-v1-12-implementation-plan.md`

