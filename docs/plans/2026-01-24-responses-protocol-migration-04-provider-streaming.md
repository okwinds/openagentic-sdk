# Responses Protocol Migration — Chapter 4: Provider (Streaming SSE `/responses`)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `/responses` streaming: parse SSE chunks, emit incremental text deltas, and finalize client-side function tool calls.

**Architecture:** Implement a Responses SSE state machine modeled after `OPENAI_RESPONSES_IMPLEMENTATION.md`:
- track `currentTextId`
- track `ongoingToolCalls` by `output_index` and accumulate `function_call_arguments.delta`
- on `response.output_item.done` for `function_call`, finalize a `ToolCall`
- on `response.completed/incomplete`, emit a finish marker that carries usage + response_id

**Tech Stack:** existing `parse_sse_events`, new Responses chunk parsing, `unittest`.

---

### Task 1: Streaming provider emits text deltas + tool calls

**Files:**
- Modify: `openagentic_sdk/providers/openai_responses.py`
- Test: `tests/test_openai_responses_provider_stream.py`

**Step 1: Write the failing test**

Simulate SSE:
- `response.created` (with `response.id`)
- `response.output_item.added` (message)
- `response.output_text.delta` (text)
- `response.output_item.added` (function_call)
- `response.function_call_arguments.delta` (arguments streaming)
- `response.output_item.done` (function_call done)
- `response.completed` then `[DONE]` (or provider EOF)

Assert:
- yields `text_delta` events that join to the final text
- yields exactly one `tool_call` with parsed JSON args
- yields `done`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_openai_responses_provider_stream -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement streaming loop:
- parse SSE `data:` payloads into JSON objects
- handle event types listed above
- ignore unknown events safely

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_openai_responses_provider_stream -v`
Expected: PASS

