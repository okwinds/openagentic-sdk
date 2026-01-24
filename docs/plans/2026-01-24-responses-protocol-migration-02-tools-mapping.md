# Responses Protocol Migration — Chapter 2: Tools Mapping (Function + Built-in)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Map SDK tool schemas to Responses `tools[]` and normalize tool call/outputs across function tools (client-executed) and built-in tools (provider-executed).

**Architecture:** Introduce `tool_schemas_for_responses()` that emits Responses-style tool definitions. Keep the existing OpenAI chat schema generator for compatibility where needed, but migrate runtime/providers to Responses schemas.

**Tech Stack:** Python, existing `openagentic_sdk/tools/openai.py` patterns, `unittest`.

---

### Task 1: Add Responses tool schema generator

**Files:**
- Create: `openagentic_sdk/tools/openai_responses.py`
- Modify: `openagentic_sdk/tools/__init__.py` (if needed)
- Test: `tests/test_openai_responses_tool_schemas.py`

**Step 1: Write the failing test**

Create a test asserting:
- `tool_schemas_for_responses(["Read"])` returns a tool with `{type:"function", name:"Read", ...}` (no nested `"function": {...}`)
- parameters match the existing `tool_schemas_for_openai` definitions for the same tool

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_openai_responses_tool_schemas -v`
Expected: FAIL (missing module)

**Step 3: Write minimal implementation**

Implement `tool_schemas_for_responses()` by adapting the existing schema dicts:
- lift `function.name/description/parameters` to top-level fields
- optionally set `strict` to `True` for deterministic JSON args if desired (keep `False` if unsure)

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_openai_responses_tool_schemas -v`
Expected: PASS

---

### Task 2: Update CLI/tool tests expecting OpenAI schemas

**Files:**
- Modify: `tests/test_openai_tool_schemas.py`
- Modify: `tests/test_cli_provider_tool_schemas.py`

**Step 1: Write the failing test**

Update assertions to match Responses schema format for the default RIGHTCODE provider path.

**Step 2: Run tests to verify it fails**

Run: `python -m unittest tests.test_openai_tool_schemas tests.test_cli_provider_tool_schemas -v`
Expected: FAIL

**Step 3: Update implementation/tests to pass**

Adjust tests to call the correct schema generator used by runtime after migration.

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_openai_tool_schemas tests.test_cli_provider_tool_schemas -v`
Expected: PASS

