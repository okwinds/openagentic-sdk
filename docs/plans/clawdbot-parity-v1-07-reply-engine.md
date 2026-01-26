# Clawdbot Parity v1 — Reply Engine (Unified Message Handling)

## Analysis (Clawdbot)

Clawdbot’s Reply Engine responsibilities (high-level):

- parse session/routing
- command authorization
- model selection and directives
- media/link understanding (optional)
- run agent
- produce outbound payloads

Entry: `src/auto-reply/reply/get-reply.ts`

## Current State (openagentic-sdk)

SDK can run an agent loop on a string prompt and produce:

- streamed events (`openagentic_sdk.query`)
- final text (`openagentic_sdk.run`)

SDK does not know about “channels”, “payloads”, or message envelopes.

## Design (v1 scope)

Implement `ReplyEngine` in `openagentic_gateway`:

Inputs:

- `InboundEnvelope` (channel/account/peer + message)
- optional `ReplyOptions` (force agent, force model, metadata)

Outputs:

- `OutboundPayload[]` (at minimum: `send_text`)

### Prompt shaping (v1)

We keep it simple and safe:

- system prompt remains SDK-driven (`setting_sources=["project"]` etc.)
- user prompt becomes:
  - a rendered envelope header (who/where)
  - followed by message text
  - attachments as references (future)

### Commands

Align with existing SDK behavior:

- allow `/name ...` pass-through (SDK already expands slash commands when present in project)
- Gateway may add “channel-aware” commands later (v2)

## Plan (Implementation Outline)

1) Unit tests:
   - envelope → prompt rendering
   - text chunking rules (if needed)
2) Integration test (using test channel + fake provider):
   - inbound message → agent run → outbound payload
3) Add Gateway endpoint:
   - `POST /v1/chat/inbound` calls ReplyEngine and returns payloads
4) Add channel adapter:
   - on inbound event, call ReplyEngine; send payloads via `plugin.send()`

## TDD

Use a fake provider or deterministic provider stub so tests never hit network.

## Acceptance Checklist

- Inbound envelope yields a prompt with the right identity fields.
- ReplyEngine returns a deterministic outbound payload array.
- A channel plugin can deliver inbound and send outbound via the ReplyEngine.

