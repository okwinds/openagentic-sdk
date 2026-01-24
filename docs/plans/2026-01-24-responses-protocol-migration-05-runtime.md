# Responses Protocol Migration — Chapter 5: Runtime Refactor (Responses-Native Loop)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor runtime to use Responses-native calls and tool output continuation, instead of building chat-completions `messages[]`.

**Architecture:** Maintain a `ResponsesConversationState` per session:
- first call: `input=[{role:"system"...},{role:"user"...}]`, `store=True`
- next calls: use `previous_response_id` from the last response, and send only the new `input` items (user message and any `function_call_output` items from tool execution)

**Tech Stack:** Python, existing runtime tool loop, `unittest`.

---

### Task 1: Add Responses-mode provider calls in runtime

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/providers/base.py` (provider protocol)
- Test: `tests/test_runtime_tool_loop.py`
- Test: `tests/test_runtime_streaming.py`

**Step 1: Write the failing test**

Add a fake provider that:
- records `previous_response_id` and `input`
- returns a `response_id`
- returns a `ToolCall` requiring execution, then a final assistant text after tool output is sent

Assert:
- runtime sends tool output as `function_call_output` in the next `/responses` call
- runtime uses the last `response_id` as `previous_response_id`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_runtime_tool_loop tests.test_runtime_streaming -v`
Expected: FAIL

**Step 3: Implement minimal runtime refactor**

Update runtime loop to:
- stop constructing chat `messages[]`
- build Responses `input[]` items
- execute tools based on returned `ToolCall`s
- append `function_call_output` items for tool results
- persist the latest `response_id` into the `Result` event

**Step 4: Run tests to verify it passes**

Run: `python -m unittest tests.test_runtime_tool_loop tests.test_runtime_streaming -v`
Expected: PASS

