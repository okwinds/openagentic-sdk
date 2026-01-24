# Responses Protocol Migration (RIGHTCODE) — Macro Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the OpenAI Responses protocol end-to-end (non-stream + streaming SSE) and migrate RIGHTCODE defaults from `/chat/completions` to `/responses`.

**Architecture:** Refactor the SDK runtime to become Responses-native: maintain `previous_response_id` + incremental `input[]` items, execute client-side function tools, and feed `function_call_output` back into the conversation via `/responses`.

**Tech Stack:** Python 3.11+, stdlib `urllib.request`, dataclasses, `unittest`.

---

## Chapter 1 — Protocol + Internal State

Define the SDK’s internal representation for a Responses-native conversation, including how we persist and resume `previous_response_id`.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-01-protocol-and-state.md`

## Chapter 2 — Tools Mapping (Function + Built-in)

Define how SDK tools map to Responses `tools[]` and how we treat built-in tools (provider-executed) vs client tools (SDK-executed).

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-02-tools-mapping.md`

## Chapter 3 — Provider: Non-Streaming `/responses`

Implement non-streaming request/response mapping: build request body, parse `output[]`, extract assistant text + client-side tool calls, capture usage/metadata/response id.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-03-provider-nonstream.md`

## Chapter 4 — Provider: Streaming SSE `/responses`

Implement SSE event parsing + state machine per `OPENAI_RESPONSES_IMPLEMENTATION.md`, emitting text deltas + final client-side tool calls; capture finish reason + usage + response id.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-04-provider-streaming.md`

## Chapter 5 — Runtime Refactor (Responses-Native Loop)

Refactor runtime to call the new Responses provider APIs, handle streaming deltas, execute client tools, and send `function_call_output` items back (continuing from `previous_response_id`).

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-05-runtime.md`

## Chapter 6 — Session Resume (Responses)

Persist and rebuild Responses conversation state from event logs; preserve backward compatibility for older sessions as a best-effort fallback.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-06-session-resume.md`

## Chapter 7 — CLI/Examples Migration (RIGHTCODE)

Switch CLI/examples defaults to the Responses provider; update docs/env vars and any assumptions about `/chat/completions`.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-07-cli-examples.md`

## Chapter 8 — Verification

Update/replace tests for providers/tools/runtime to cover `/responses` behavior and streaming; run full suite.

Detail plan: `docs/plans/2026-01-24-responses-protocol-migration-08-verification.md`

