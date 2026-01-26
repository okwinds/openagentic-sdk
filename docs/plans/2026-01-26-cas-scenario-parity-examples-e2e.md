# CAS Scenario Parity (Examples + Real-API E2E) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Mirror the *scenarios* covered by `claude-agent-sdk-python`’s `examples/` and `e2e-tests/` using `openagentic-sdk` (without API naming/shape alignment).

**Architecture:** Add a curated “CAS-scenarios” example set under `example/` and a separate real-network `e2e_tests/` suite (unittest) that calls a real OpenAI-compatible endpoint via `RIGHTCODE_*` env vars. Keep production SDK code untouched unless a scenario is impossible to express with current public APIs.

**Tech Stack:** Python 3.11+, `unittest` (`IsolatedAsyncioTestCase`), `asyncio`, `openagentic_sdk` runtime + tools + hooks, `OpenAIResponsesProvider` (or rightcode-compatible base URL).

---

## 0) Scenario Inventory (Source of Truth)

### CAS examples (scenarios to mirror)

From `/mnt/e/development/claude-agent-sdk-python/examples/`:

- `quick_start.py`
  - One-shot query stream → print assistant text
  - Options: system prompt, max turns
  - Tools: allow Read/Write, do a small file task
- `streaming_mode.py`
  - `example_basic_streaming` (client context manager, one query)
  - `example_multi_turn_conversation` (multi-turn, same client)
  - `example_concurrent_responses` (background receive while sending)
  - `example_with_interrupt` (interrupt + follow-up)
  - `example_manual_message_handling` (custom parsing of stream)
  - `example_with_options` (allowed tools + env, collect tool usage)
  - `example_async_iterable_prompt` (stream user messages)
  - `example_bash_command` (tool use blocks)
  - `example_control_protocol` (runtime/control info)
  - `example_error_handling` (robust error patterns)
- `tool_permission_callback.py`
  - `can_use_tool` allow/deny + rewrite inputs + user prompt for unknown tools
- `hooks.py`
  - PreToolUse / PostToolUse / UserPromptSubmit hooks; block/continue; add context
- `include_partial_messages.py`
  - partial message streaming (deltas) on/off; thinking deltas
- `agents.py`
  - define custom agents and invoke them via prompt
- `filesystem_agents.py`
  - load `.claude/agents/*.md` via `setting_sources=["project"]`
- `setting_sources.py`
  - default vs user-only vs project+user settings (visibility in init/system message)
- `mcp_calculator.py`
  - SDK MCP in-process tool server; permission enforcement; multi-step calc
- `plugin_example.py`, `tools_option.py`, `system_prompt.py`, `max_budget_usd.py`, `stderr_callback_example.py`
  - feature-oriented demos (some may not exist 1:1 in OAS)

### CAS e2e tests (scenarios to mirror)

From `/mnt/e/development/claude-agent-sdk-python/e2e-tests/`:

- `test_agents_and_settings.py`
  - custom agent definition visible in init
  - filesystem agents load via setting_sources (issue regression)
  - setting_sources behaviors
- `test_dynamic_control.py`
  - change permission mode during session
  - change model during session
  - interrupt
- `test_hooks.py`
  - permission decision + reason
  - stop reason / continue control
  - additional context
- `test_include_partial_messages.py`
  - stream events on/off; thinking deltas
- `test_sdk_mcp_tools.py`
  - SDK MCP tool execution; permission enforcement; multi-tool; missing permissions
- `test_stderr_callback.py`
  - capture CLI stderr debug output
- `test_tool_permissions.py`
  - permission callback gets called for dangerous operations
- `test_structured_output.py`
  - json_schema structured output (not currently supported by OAS)

---

## 1) Target Mapping (CAS scenario → OAS implementation)

**Principles**
- Prefer “forced unknown” patterns (random token files/tools) to *guarantee* tool usage in e2e.
- Examples should be cohesive “user stories” (not micro-snippets).
- Unit tests validate scripts in offline mode; e2e tests validate real API behavior.
- **No SDK changes in this phase.** If a scenario can’t be expressed, document as a gap and (optionally) add a follow-up plan.

### Scenarios we can fully mirror now
- Quickstart query + options → `openagentic_sdk.query_messages()` and `OpenAgentSDKClient`
- Multi-turn client conversation → `OpenAgentSDKClient`
- Interrupt → `OpenAgentSDKClient.interrupt()`
- Permission callback gating → `PermissionGate(can_use_tool=...)`
- Hooks (rewrite/block) → `HookEngine(pre_tool_use=..., post_tool_use=..., user_prompt_submit=...)`
- Partial message streaming → `OpenAgenticOptions(include_partial_messages=True)` + `query_messages()`
- SDK MCP tools → `openagentic_sdk.mcp.sdk.tool` + `create_sdk_mcp_server` + `mcp_servers={...}`
- Subagent Task tool → `OpenAgenticOptions(agents={...})` + `allowed_tools=["Task"]`
- Project `.claude` memory/commands/skills visibility (partial) → `setting_sources=["project"]` (system prompt injection)

### Scenarios that are *not* 1:1 today (document gaps; don’t “fake”)
- “Async iterable prompt of *structured user messages*” (CAS): OAS prompt streaming only supports `{type:"text"}` chunks.
- “Filesystem agents from `.claude/agents/*.md`”: OAS currently does not load these as agents.
- “Dynamic control protocol” (`set_model`, `set_permission_mode`) on a live client: OAS client doesn’t expose these mutations.
- “Structured output json_schema”: OAS doesn’t expose an output schema API yet.
- “CLI stderr callback”: OAS is not CLI-subprocess based for SDK calls.

---

## 2) Example Suite Design (CAS-scenarios)

**Files**
- Create: `example/cas_01_quickstart.py`
- Create: `example/cas_02_client_streaming_and_multiturn.py`
- Create: `example/cas_03_interrupt.py`
- Create: `example/cas_04_permissions_callback.py`
- Create: `example/cas_05_hooks.py`
- Create: `example/cas_06_include_partial_messages.py`
- Create: `example/cas_07_sdk_mcp_tools.py`
- Create: `example/cas_08_task_subagent.py`
- Modify: `example/README.md` (add a “CAS scenarios” section + how to run online)

**Example conventions**
- Use `example/_common.py` for env/options.
- Must run in offline mode without crashing (`OPENAGENTIC_SDK_EXAMPLE_OFFLINE=1`).
- When online, each script should create a temp working dir and/or `.openagentic-sdk/example-artifacts/...` to keep side-effects contained.

---

## 3) Real-API E2E Suite Design

**Directory:** Create `e2e_tests/` (unittest discovery friendly; avoid `e2e-tests/` hyphen).

**Auth/env:**
- Require `RIGHTCODE_API_KEY`
- Optional: `RIGHTCODE_BASE_URL`, `RIGHTCODE_MODEL`, `RIGHTCODE_TIMEOUT_S`
- Hard-fail if missing (like CAS), but only when running `e2e_tests/` explicitly.

**Files**
- Create: `e2e_tests/README.md`
- Create: `e2e_tests/_harness.py` (env + options helpers)
- Create: `e2e_tests/e2e_quickstart.py`
- Create: `e2e_tests/e2e_tool_loop_filesystem.py`
- Create: `e2e_tests/e2e_permissions_callback.py`
- Create: `e2e_tests/e2e_hooks.py`
- Create: `e2e_tests/e2e_include_partial_messages.py`
- Create: `e2e_tests/e2e_sdk_mcp_tools.py`
- Create: `e2e_tests/e2e_task_subagent.py`

**Run commands**
- Unit tests: `python3 -m unittest -q`
- E2E tests: `python3 -m unittest discover -s e2e_tests -p "e2e_*.py" -v`

---

## 4) TDD Execution Plan (bite-sized)

### Task 1: Add the plan-visible “CAS scenarios” section to examples README

**Files:**
- Modify: `example/README.md`

**Step 1 (RED):** Add a unit test that asserts the README references the new scripts by filename.

- Create: `tests/test_examples_cas_readme.py`

**Step 2:** Run: `python3 -m unittest -q tests.test_examples_cas_readme`
Expected: FAIL (scripts not present yet).

**Step 3 (GREEN):** Update `example/README.md` to add a “CAS scenarios” section listing the planned filenames.

**Step 4:** Re-run the test; Expected: PASS.

### Task 2: CAS Quickstart scenario example + offline smoke test

**Files:**
- Create: `example/cas_01_quickstart.py`
- Test: `tests/test_examples_cas_scripts_offline.py` (subprocess smoke runner)

**Step 1 (RED):** In `tests/test_examples_cas_scripts_offline.py`, add a test that runs:
- `python3 scripts/verify_examples.py --offline --only cas_01_quickstart`
and expects exit code 0.

**Step 2:** Run that single test; Expected: FAIL (file missing).

**Step 3 (GREEN):** Implement `example/cas_01_quickstart.py`:
- Use `openagentic_sdk.query_messages()` (or `run()` for one-shot) to show assistant output printing.
- Keep it resilient in offline mode.

**Step 4:** Re-run test; Expected: PASS.

### Task 3: Implement remaining CAS scenario examples (repeat TDD loop)

Repeat Task 2 pattern for:
- `example/cas_02_client_streaming_and_multiturn.py`
- `example/cas_03_interrupt.py`
- `example/cas_04_permissions_callback.py`
- `example/cas_05_hooks.py`
- `example/cas_06_include_partial_messages.py`
- `example/cas_07_sdk_mcp_tools.py`
- `example/cas_08_task_subagent.py`

Each file should get:
- (RED) offline smoke test entry
- (GREEN) implement minimal script
- (REFACTOR) keep scripts cohesive, not fragmented

### Task 4: Add E2E harness + first real-API test (Quickstart)

**Files:**
- Create: `e2e_tests/_harness.py`
- Create: `e2e_tests/test_quickstart.py`
- Create: `e2e_tests/README.md`

**Step 1 (RED):** Write `e2e_tests/test_quickstart.py`:
- Build options from env (`RIGHTCODE_API_KEY` required)
- Call `openagentic_sdk.run(prompt=..., options=...)`
- Assert non-empty `final_text` and `session_id`

**Step 2:** Run: `python3 -m unittest discover -s e2e_tests -v`
Expected: FAIL if env missing; otherwise should PASS with network.

**Step 3 (GREEN):** Implement `_harness.py` and README to make the run instructions explicit.

### Task 5: Real-API tool-loop E2E (forced-unknown file read/write/edit)

**Files:**
- Create: `e2e_tests/test_tool_loop_filesystem.py`

**Step 1 (RED):** Write test that:
- Creates temp dir + random token file
- Runs a prompt that MUST Read the file and echo the token
- Asserts the token appears in final output **and** a `tool.use` event with `Read` occurred (use `openagentic_sdk.query()` and collect events)

**Step 2:** Run; verify it fails for the right reason if scenario isn’t implemented.

**Step 3 (GREEN):** Adjust prompts/allowed tools to make it reliable:
- Use random token to prevent guessing
- Set `allowed_tools=["Read"]` for the read test; `permission_mode="bypass"` for the gate

### Task 6: Real-API permissions callback E2E

**Files:**
- Create: `e2e_tests/test_permissions_callback.py`

Test patterns:
- Deny `Write` and verify file did not change + tool.result is error
- Allow `Write` and verify file exists

### Task 7: Real-API hooks E2E (rewrite Read target)

**Files:**
- Create: `e2e_tests/test_hooks.py`

Test pattern:
- PreToolUse hook rewrites `Read.file_path` from `a.txt` → `b.txt`
- Randomize token in `b.txt` and assert output returns that token

### Task 8: Real-API partial streaming E2E

**Files:**
- Create: `e2e_tests/test_include_partial_messages.py`

Test pattern:
- Set `include_partial_messages=True`
- Use `query_messages()` and assert at least one `StreamEvent` then final `AssistantMessage` then `ResultMessage`

### Task 9: Real-API SDK MCP tools E2E (forced-unknown tool output)

**Files:**
- Create: `e2e_tests/test_sdk_mcp_tools.py`

Test pattern:
- Create a tool that returns a random token
- Prompt: “Call `mcp__x__get_token` and print exactly the token”
- Assert tool was used and token matches

### Task 10: Real-API subagent Task E2E

**Files:**
- Create: `e2e_tests/test_task_subagent.py`

Test pattern:
- Parent allowed_tools = ["Task"] only
- Define agent with tools=["Read"], prompt instructing it to read token file
- Assert parent emits `tool.use` Task and final output contains token

---

## 5) “Gap” Tracking (follow-up plan if desired)

Create a follow-up plan only if you want to actually close gaps:
- `.claude/agents` filesystem agent loading
- structured output support (json_schema)
- richer prompt streaming (structured message stream)
- dynamic per-session mutation (set model/permission mode)
