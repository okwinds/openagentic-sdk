# Responses Protocol Migration — Chapter 8: Verification

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure the full test suite passes after the migration, and that streaming/tool loops behave as expected.

---

### Task 1: Replace legacy OpenAI chat provider tests with Responses tests

**Files:**
- Modify: `tests/test_openai_provider_non_stream.py`
- Modify: `tests/test_openai_provider_stream.py`
- Modify: `tests/test_openai_compatible_provider.py`
- Modify: `tests/test_openai_compatible_retry.py`

**Step 1: Update tests to hit `/responses`**

Refactor fixtures to use Responses payloads and simulated SSE event streams.

**Step 2: Run targeted provider tests**

Run: `python -m unittest tests.test_openai_provider_non_stream tests.test_openai_provider_stream tests.test_openai_compatible_provider tests.test_openai_compatible_retry -v`
Expected: PASS

---

### Task 2: Run full suite

Run: `python -m unittest -v`
Expected: PASS

