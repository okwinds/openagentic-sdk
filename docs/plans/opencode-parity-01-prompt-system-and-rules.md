# Parity 01: Prompt System + Rules (AGENTS.md / instructions)

Status: implemented (initial slice) in this repo:

- First-class `OpenAgenticOptions.system_prompt`
- Project/global `AGENTS.md` injection when `setting_sources` includes "project"
- `OpenAgenticOptions.instruction_files` (file/glob) injected into system prompt
- Implementation: `openagentic_sdk/prompt_system.py` + runtime integration in `openagentic_sdk/runtime.py`
- Tests: `tests/test_system_prompt_layering.py`

## Analysis

OpenCode prompt management is layered and configurable:

- Provider/model system/header templates: `opencode/packages/opencode/src/session/prompt/*.txt`
- Selection/injection: `opencode/packages/opencode/src/session/system.ts`
- Agent prompts (plan/build/explore/summary/title/compaction):
  - `opencode/packages/opencode/src/agent/prompt/*.txt`
  - `opencode/packages/opencode/src/agent/agent.ts`
- Rules/instructions from multiple sources (project + global + URL + globs):
  - `opencode/packages/opencode/src/config/config.ts`
  - `opencode/packages/opencode/src/session/system.ts`

Current repo has:

- Tool-level long descriptions in `openagentic_sdk/tool_prompts/*.txt`
- Project memory from `CLAUDE.md` only, plus `.claude/commands` index: `openagentic_sdk/project/claude.py`
- No first-class `system_prompt` API on `OpenAgenticOptions` (system injection is currently coupled to `.claude` + CLI hooks).

Parity target:

- First-class, stable system prompt layer.
- Rules file support equivalent to OpenCode: at minimum `AGENTS.md` + config-driven `instructions[]` (file/glob/url).
- Agent prompt layering for built-in subagents (plan/build/explore/etc) as shipped presets.

## Plan

### API Surface

- Add `OpenAgenticOptions.system_prompt` (string or preset/append structure).
- Add optional `OpenAgenticOptions.instructions` (resolved strings) or a config loader that produces them.
- Extend project settings loader to also read `AGENTS.md` (project + global) and merge with `.claude/CLAUDE.md`.

### Data Model

- Define a deterministic layering order, e.g.:
  1) Base system prompt preset (optional)
  2) Provider header prompt (optional, depends on provider)
  3) Agent prompt (when using Task/subagent presets)
  4) Rules/instructions (AGENTS.md, CLAUDE.md, config instructions)
  5) Runtime/CLI context injection (optional)

### Acceptance Criteria

- SDK user can set system prompt programmatically without using hooks.
- When project settings are enabled, rules are loaded deterministically and appear in the system message.
- Unit tests cover precedence/merge order and file discovery.

## TDD (Red/Green)

- Add tests that:
  - Assert system message includes `OpenAgenticOptions.system_prompt` content.
  - Assert `AGENTS.md` is discovered and merged.
  - Assert `instructions[]` file/glob/url resolution is deterministic.

## Review Checklist

- No prompt injection from untrusted sources without explicit opt-in.
- Deterministic ordering; no duplicates.
- Backwards compatible default behavior.

## Retry Strategy

- If tests reveal ambiguity in layering, lock it down with explicit precedence rules and update tests.
