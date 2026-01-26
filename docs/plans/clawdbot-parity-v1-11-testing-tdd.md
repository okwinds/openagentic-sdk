# Clawdbot Parity v1 — Testing Strategy (TDD, Red/Green, “No Excuses”)

## Why This Doc Exists

The user requirement is explicit: **分析-设计-落地计划-TDD-红绿灯-回顾-下一个任务**.

So this doc is the default playbook for every task in `clawdbot-parity-v1-12-implementation-plan.md`.

## Test Pyramid

1) Unit tests (fast, deterministic)
   - routing/session key logic
   - plugin registry/loader
   - auth/scope decisions
2) Contract tests (HTTP surface)
   - start server on ephemeral port and assert response shapes
3) Integration tests (end-to-end)
   - “test channel” inbound → ReplyEngine → AgentCore stub → outbound payload
4) E2E tests (optional, slower)
   - real Telegram webhook with a dev token (gated by env vars)

## Red/Green Checklist (Per Change)

1) **Red**: add a failing test that proves the behavior gap
2) Run the smallest possible test command and verify it fails for the expected reason
3) **Green**: implement the minimal code to pass
4) Re-run the same test command and verify pass
5) Refactor only if necessary (still green)
6) Add one more test for an edge case (repeat)

## Suggested Test Harness Conventions

- Use `unittest` (repo default) unless we explicitly decide to add pytest later.
- Prefer dependency injection:
  - fake provider (no network)
  - fake channel plugin
  - temp dirs for stores

## Gatekeeping Rules

- No merging “design-only” assumptions into code without a failing test.
- No “it should work” claims without a command we can run.
- Every public Gateway endpoint must have at least one contract test.

## Commands

- Unit tests: `python -m unittest -q`
- Targeted module: `python -m unittest -q tests.test_gateway_auth`

## “Red/Green Light” Definition

- Red = test fails for the intended behavior gap (not for unrelated breakage)
- Green = minimal tests pass
- Refactor = optional; must stay green

