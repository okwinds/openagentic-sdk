# Responses Protocol Migration — Chapter 3: Provider (Non-Streaming `/responses`)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `POST /responses` (non-stream) for OpenAI and OpenAI-compatible providers, including tool calls parsing and `response_id` capture.

**Architecture:** Create a `OpenAIResponsesProviderBase` using a configurable `base_url` + `api_key_header`. Build request payload with `input`, `tools`, `tool_choice`, `store`, `include`, `previous_response_id`. Parse `output[]` into assistant text + client-side function tool calls.

**Tech Stack:** stdlib `urllib.request`, `json`, dataclasses, `unittest`.

---

### Task 1: Implement provider request body + parsing

**Files:**
- Create: `openagentic_sdk/providers/openai_responses.py`
- Modify: `openagentic_sdk/providers/__init__.py`
- Test: `tests/test_openai_responses_provider_non_stream.py`

**Step 1: Write the failing test**

Test expectations:
- provider calls `.../responses` (not `/chat/completions`)
- payload includes `model`, `input`, and `tools` when provided
- parsing converts a `function_call` output item into `ToolCall`
- parsing concatenates `message.output_text` into `assistant_text`
- captures `response.id` as `response_id`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_openai_responses_provider_non_stream -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement:
- auth header rules (Bearer when `api_key_header=authorization`)
- `_default_transport` with retries (reuse from `openai_compatible.py`)
- `complete_responses(...) -> ModelOutput` (or new output type), filling `response_id`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_openai_responses_provider_non_stream -v`
Expected: PASS

