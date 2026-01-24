# Responses Protocol Migration — Chapter 1: Protocol + Internal State

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce Responses-native request/response types and conversation state (`previous_response_id`), and wire the state through options/runtime/events.

**Architecture:** Add a lightweight `ResponsesConversationState` and `ResponsesModelOutput` that carry `response_id` and `provider_metadata`. Persist `response_id` in the session event log and rebuild it on resume.

**Tech Stack:** Python dataclasses, `unittest`.

---

### Task 1: Add Responses conversation state types

**Files:**
- Create: `openagentic_sdk/providers/responses_types.py`
- Modify: `openagentic_sdk/providers/base.py`
- Test: `tests/test_responses_types.py`

**Step 1: Write the failing test**

Create `tests/test_responses_types.py` asserting:
- a `ResponsesConversationState(previous_response_id="r1")` stores the id
- a `ResponsesModelOutput(response_id="r2")` carries response id and tool calls

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_responses_types -v`
Expected: FAIL (missing module/classes)

**Step 3: Write minimal implementation**

Create `openagentic_sdk/providers/responses_types.py`:
- `ResponsesConversationState(previous_response_id: str | None = None, store: bool = True, include: tuple[str, ...] = ())`
- `ResponsesModelOutput(assistant_text, tool_calls, usage, raw, response_id, provider_metadata)`

Update `openagentic_sdk/providers/base.py`:
- extend `ModelOutput` OR add a parallel output type used by Responses provider (preferred: extend with optional `response_id` + `provider_metadata` fields).

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_responses_types -v`
Expected: PASS

---

### Task 2: Persist response id in events

**Files:**
- Modify: `openagentic_sdk/events.py`
- Modify: `openagentic_sdk/serialization.py`
- Test: `tests/test_events_roundtrip.py`
- Test: `tests/test_event_backward_compat.py`

**Step 1: Write the failing test**

Add/extend tests to assert:
- `Result` event can carry `provider_metadata` and `response_id` fields
- roundtrip serialization preserves them
- older logs without these fields still load (back-compat)

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_events_roundtrip tests.test_event_backward_compat -v`
Expected: FAIL (fields missing)

**Step 3: Write minimal implementation**

Update `openagentic_sdk/events.py`:
- add optional `response_id: str | None = None`
- add optional `provider_metadata: Mapping[str, Any] | None = None` (or `dict[str, Any] | None`)

Ensure `serialization.event_from_dict()` remains tolerant (it already filters unknown fields).

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_events_roundtrip tests.test_event_backward_compat -v`
Expected: PASS

