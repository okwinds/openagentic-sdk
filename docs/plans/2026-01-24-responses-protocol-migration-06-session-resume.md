# Responses Protocol Migration — Chapter 6: Session Resume (Responses)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resume sessions by rebuilding `previous_response_id` from stored events, avoiding reconstruction of full chat history.

**Architecture:** Scan session events for the most recent `result.response_id`. If not present (legacy session), either:
- fall back to legacy chat-history rebuild (best-effort), OR
- start a new Responses chain (documented behavior).

**Tech Stack:** Python, `unittest`.

---

### Task 1: Implement resume state rebuild

**Files:**
- Modify: `openagentic_sdk/runtime.py`
- Modify: `openagentic_sdk/sessions/rebuild.py`
- Test: `tests/test_resume_rebuild_messages.py` (rename/repurpose)
- Test: `tests/test_resume_limits.py`

**Step 1: Write the failing test**

Create a synthetic event log where:
- first run produces `Result(response_id="r1")`
- second run resumes and should call provider with `previous_response_id="r1"`

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_resume_rebuild_messages tests.test_resume_limits -v`
Expected: FAIL

**Step 3: Implement rebuild logic**

Add `rebuild_responses_state(events, ...) -> ResponsesConversationState`.
Update runtime resume path to use it.

**Step 4: Run tests to verify it passes**

Run: `python -m unittest tests.test_resume_rebuild_messages tests.test_resume_limits -v`
Expected: PASS

