# Skill System (OpenCode-style) Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align Skills behavior with OpenCode: single `Skill` tool, remove legacy skill-tool surface, and implement multi-root discovery (project `.claude` + global `~/.openagentic-sdk`).

**Architecture:** Replace the current multi-tool surface with a single `Skill` tool that accepts only `name`. Provide `<available_skills>` via the tool description (dynamic at schema-build time). Implement skill discovery across two roots with clear precedence: project skills override global skills.

**Tech Stack:** Python stdlib (`pathlib`, `os`), existing SDK tool/runtime/event architecture, `unittest`.

---

### Task 1: Remove legacy Skill tools (surface)

**Files:**
- Delete: `openagentic_sdk/tools/skill_list.py`
- Delete: `openagentic_sdk/tools/skill_load.py`
- Delete: `openagentic_sdk/tools/skill_activate.py`
- Modify: `openagentic_sdk/tools/defaults.py`
- Modify: `openagentic_sdk/tools/openai.py`
- Modify: `openagentic_cli/permissions.py`
- Modify: `openagentic_cli/trace.py`
- Modify: `openagentic_sdk/permissions/gate.py`

**Step 1: Delete legacy tool implementations**

**Step 2: Remove legacy tools from default registry**

**Step 3: Remove legacy tools from OpenAI tool schemas**

**Step 4: Update CLI allowlists/trace filters to remove legacy names**

**Step 5: Run tests**

Run: `python -m unittest -q`
Expected: FAIL (tests/docs still reference legacy tools)

---

### Task 2: Align `Skill` tool contract with OpenCode

**Files:**
- Modify: `openagentic_sdk/tools/skill.py`
- Modify: `openagentic_sdk/tool_prompts/skill.txt`
- Modify: `openagentic_sdk/tools/openai.py`
- Test: `tests/test_skill_tool.py`
- Test: `tests/test_openai_tool_schemas.py`

**Step 1: Update tool prompt to document `Skill(name)` only**

**Step 2: Make `Skill` accept only `name` and always load**
- Reject empty/missing `name` with a clear error
- Return a dict containing an `output` string including “Base directory”

**Step 3: Update the OpenAI schema for `Skill`**
- Remove the `action` parameter
- Require `name`

**Step 4: Update unit tests to match**

**Step 5: Run targeted tests**

Run: `python -m unittest -q tests.test_skill_tool tests.test_openai_tool_schemas`
Expected: PASS

---

### Task 3: Implement multi-root discovery (project + global)

**Files:**
- Modify: `openagentic_sdk/skills/index.py`
- Modify: `openagentic_sdk/skills/parse.py`
- Test: `tests/test_skill_index.py`

**Step 1: Add helper to strip frontmatter content**

**Step 2: Update discovery roots**
- Project (compat): `<project>/.claude/{skill,skills}/**/SKILL.md`
- Global: `$OPENAGENTIC_SDK_HOME/{skill,skills}/**/SKILL.md` (defaults to `~/.openagentic-sdk`)

**Step 3: Implement precedence**
- Project overrides global when `name` conflicts

**Step 4: Add tests**
- Global skills included when `OPENAGENTIC_SDK_HOME` is set to a temp dir
- Precedence behavior is correct

**Step 5: Run targeted tests**

Run: `python -m unittest -q tests.test_skill_index`
Expected: PASS

---

### Task 4: Remove skill activation/event surface

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/events.py`
- Modify: `openagentic_sdk/serialization.py`
- Delete: `tests/test_skill_activate_runtime.py`
- Delete: `tests/test_skill_activate_resume.py`
- Modify: `tests/test_execute_skill_prompt_expand.py`
- Modify: `tests/test_runtime_skill_injection.py`

**Step 1: Remove skill activation handling and related event**

**Step 2: Update prompt helpers**
- “执行技能 <name>” rewrite should instruct using `Skill(name)` (no inlining SKILL.md)
- “list skills” rewrite should instruct reading `<available_skills>` from tool description

**Step 3: Update tests**

**Step 4: Run targeted tests**

Run: `python -m unittest -q tests.test_execute_skill_prompt_expand tests.test_runtime_skill_injection`
Expected: PASS

---

### Task 5: Purge docs mentioning legacy tools

**Files:**
- Modify: `README.md`
- Modify: `README.zh_cn.md`
- Modify: `PROJECT_REPORT.md`

**Step 1: Remove any mention of removed legacy tools**

**Step 2: Ensure docs describe only `Skill(name)`**

**Step 3: Run full test suite**

Run: `python -m unittest -q`
Expected: PASS
