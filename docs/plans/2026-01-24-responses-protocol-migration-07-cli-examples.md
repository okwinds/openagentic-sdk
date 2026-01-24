# Responses Protocol Migration — Chapter 7: CLI/Examples Migration (RIGHTCODE)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate CLI and examples to the Responses provider and RIGHTCODE `/responses` defaults.

**Architecture:** Replace uses of `OpenAICompatibleProvider` with the new Responses provider. Keep env var names (`RIGHTCODE_*`) but point defaults and tests at `/responses`.

**Tech Stack:** Python, CLI config, `unittest`.

---

### Task 1: Update CLI provider builder

**Files:**
- Modify: `openagentic_cli/config.py`
- Modify: `example/_common.py`
- Modify: `README.md`
- Modify: `README.zh_cn.md`
- Test: `tests/test_cli_config.py`
- Test: `tests/test_cli_provider_tool_schemas.py`

**Step 1: Write the failing test**

Update tests to assert the default provider is the Responses provider and uses `/responses`.

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_config tests.test_cli_provider_tool_schemas -v`
Expected: FAIL

**Step 3: Implement migration**

Switch provider type in CLI/examples and update docs.

**Step 4: Run tests to verify it passes**

Run: `python -m unittest tests.test_cli_config tests.test_cli_provider_tool_schemas -v`
Expected: PASS

