# OpenCode Parity v2 — Prompt System + Rules

## Source of Truth (OpenCode)

- Prompt selection + rules loading: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`
- Prompt templates:
  - `/mnt/e/development/opencode/packages/opencode/src/session/prompt/*.txt`
  - Notable imports in `system.ts`:
    - `./prompt/anthropic.txt`
    - `./prompt/qwen.txt` (used as "without todo" prompt)
    - `./prompt/beast.txt`
    - `./prompt/gemini.txt`
    - `./prompt/anthropic_spoof.txt`
    - `./prompt/codex_header.txt`

## Current State (openagentic-sdk)

Primary implementation: `openagentic_sdk/prompt_system.py`

Runtime wiring (Codex/OAuth special-case and provider protocol mapping): `openagentic_sdk/runtime.py`

Prompt templates (embedded): `openagentic_sdk/opencode_prompts/*.txt`

Currently implemented (close to parity, with one explicit non-parity extension):

- Provider/model prompt selection and provider header injection (OpenCode `SystemPrompt.provider()` + `SystemPrompt.header()`):
  - `openagentic_sdk/prompt_system.py` (`_opencode_provider_prompt`, `_opencode_header`)
  - templates:
    - `openagentic_sdk/opencode_prompts/anthropic.txt`
    - `openagentic_sdk/opencode_prompts/qwen.txt` (fallback)
    - `openagentic_sdk/opencode_prompts/beast.txt`
    - `openagentic_sdk/opencode_prompts/gemini.txt`
    - `openagentic_sdk/opencode_prompts/anthropic_spoof.txt`
    - `openagentic_sdk/opencode_prompts/codex_header.txt`
- Environment prompt block (`SystemPrompt.environment()`):
  - `openagentic_sdk/prompt_system.py` (`_opencode_environment_block`)
  - Note: file tree listing is currently disabled in OpenCode and is kept empty here too.
- Rules/instructions discovery (`SystemPrompt.custom()`):
  - local rule files priority/early-stop: `AGENTS.md` then `CLAUDE.md` then `CONTEXT.md` (deprecated)
  - global rule files priority/early-stop
  - `config.instructions` support:
    - URL fetch with timeout 5s, failure-to-empty
    - `~/` expansion
    - absolute basename glob semantics
    - relative glob-up semantics + project-discovery-disabled behavior
  - `openagentic_sdk/prompt_system.py` (`_custom_instruction_blocks`, `_resolve_relative_instruction`)
- Codex/OpenAI OAuth special-casing (OpenCode: Responses `instructions` + system-as-user-message):
  - builder returns `BuiltSystemPrompt(system_text, instructions, is_codex_session)`
  - runtime uses `instructions` for Responses providers and sets `role: user` for the joined system content in Codex sessions
  - `openagentic_sdk/prompt_system.py` + `openagentic_sdk/runtime.py`

Explicit non-parity extension (optional):

- OpenAgentic `.claude` compatibility blocks (project memory + commands list) are supported but gated behind
  `"claude" in setting_sources`:
  - `openagentic_sdk/prompt_system.py` (`_claude_project_blocks`)
  - loader: `openagentic_sdk/project/claude.py`

## OpenCode Behavior (Detailed)

### 1) Provider/model prompt selection

OpenCode selects provider prompt blocks based on `model.api.id`:

- If contains `gpt-5`: use `PROMPT_CODEX` (`codex_header.txt`)
- Else if contains `gpt-` OR `o1` OR `o3`: use `PROMPT_BEAST`
- Else if contains `gemini-`: use `PROMPT_GEMINI`
- Else if contains `claude`: use `PROMPT_ANTHROPIC`
- Else: use `PROMPT_ANTHROPIC_WITHOUT_TODO` (imported from `qwen.txt`)

Reference: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts` `SystemPrompt.provider()`

### 1.1) Final system prompt assembly order (critical)

OpenCode assembles the final system prompt as a list of system-message strings, then joins them with `\n\n`.

Order (high level):

1. Optional provider header(s) (`SystemPrompt.header(providerID)`).
2. Base prompt:
   - If `input.agent.prompt` is present, use that.
   - Else (non-Codex sessions only), use `SystemPrompt.provider(model)`.
3. `input.system` (in normal chat flow this includes environment + custom rules/instructions).
4. `input.user.system` (highest precedence, appended last).

References:

- Assembly logic: `/mnt/e/development/opencode/packages/opencode/src/session/llm.ts`
- Provider selection: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`

### 1.2) Codex/OpenAI OAuth special-casing (critical)

When provider is OpenAI and auth type is OAuth ("Codex sessions"), OpenCode:

- Skips the provider prompt block.
- Sets Responses API `instructions = SystemPrompt.instructions()` (which is `codex_header.txt.trim()`).
- Sends the joined "system" content as a `role: "user"` message (not `role: "system"`).

References:

- Detection + behavior: `/mnt/e/development/opencode/packages/opencode/src/session/llm.ts`
- Instructions source: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts` (`SystemPrompt.instructions()`)
- Where `instructions` is sent to Responses: `/mnt/e/development/opencode/packages/opencode/src/provider/sdk/openai-compatible/src/responses/openai-responses-language-model.ts`

### 2) Provider header injection

- If `providerID` includes `anthropic`: prepend `PROMPT_ANTHROPIC_SPOOF`.
- Else: no header.

Reference: `SystemPrompt.header()`

### 3) Environment prompt

OpenCode adds an `<env>` block and (optionally) a `<files>` tree.

Reference: `SystemPrompt.environment()`

Note: the repo tree listing is currently disabled (hard-coded `&& false`), so `<files>` is usually empty.

### 4) Rules/instructions discovery

OpenCode loads "custom" instruction blocks from:

- Local rule files (project, search upward): `AGENTS.md`, then `CLAUDE.md`, then `CONTEXT.md` (deprecated).
  - It uses the first rule-file *kind* found and then stops scanning other kinds.
- Global rule files (first existing only):
  - `${Global.Path.config}/AGENTS.md`
  - `~/.claude/CLAUDE.md` (unless `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT`)
  - `${OPENCODE_CONFIG_DIR}/AGENTS.md` (if `OPENCODE_CONFIG_DIR` is set)

Reference: `LOCAL_RULE_FILES`, `GLOBAL_RULE_FILES`, and `SystemPrompt.custom()`

Important edge behavior:

- For local rule files: OpenCode picks the first filename kind that exists in the upward search order (AGENTS > CLAUDE > CONTEXT), and then *stops searching other kinds*.
- The upward search can yield multiple matches of the chosen filename at different ancestor directories.
- Empty/unreadable files still emit an `Instructions from: ...` header line (prompt noise).

### 5) Config-driven `instructions[]`

If `config.instructions` exists:

- URL entries (`http://` or `https://`) are fetched with a 5s timeout.
- `~/` expands to user home.
- Absolute patterns are globbed in the target directory.
- Relative patterns are resolved by `Filesystem.globUp(...)`:
  - If project discovery is enabled, resolve relative to `Instance.directory` up to `Instance.worktree`.
  - If project discovery is disabled, resolve relative to `OPENCODE_CONFIG_DIR` (otherwise skip with warning).

Reference: `resolveRelativeInstruction()` and the loop in `SystemPrompt.custom()`.

Absolute-path glob caveat:

- OpenCode only uses `basename()` as the glob and uses the `dirname()` as `cwd`. If the directory component itself contains glob tokens, it will not behave like a full absolute glob.

## Security Notes (Parity + Better-than-OpenCode)

OpenCode behavior includes surfaces that can inject arbitrary text into system prompts:

- URL instructions (`config.instructions`): remote prompt injection.
- `globUp` uses `followSymlinks:true`: possible traversal outside project root via symlinks.
- Non-git worktrees may scan to filesystem root.

Parity requires supporting these surfaces, but we should harden by default:

- URL fetch: enforce timeouts, max bytes, HTTPS-by-default, optional allowlist.
- File reads: cap size, optionally refuse symlinked targets.
- Logging: avoid printing substituted secrets in errors.

## Parity Delta (What’s Missing)

Remaining gaps vs OpenCode (prompt layer only):

- Two-part system structure optimization:
  - OpenCode keeps `system` as `[header, rest]` to preserve caching semantics after plugin transforms.
  - This repo returns a single `system_text` string (functional parity for content ordering, but not identical
    for caching behavior).
- `input.user.system` support:
  - OpenCode appends `input.user.system` at the very end (highest precedence).
  - This repo does not currently have a separate per-message system override; we only support
    programmatic `OpenAgenticOptions.system_prompt` (highest precedence at build time).
- Optional `.claude` blocks are OpenAgentic-only (not in OpenCode) and must remain explicitly opt-in.

## Plan (No-Compromise Implementation)

### API + Data Model

- Introduce a structured system prompt builder that outputs ordered blocks:
  - `header[]`
  - `provider[]`
  - `environment[]`
  - `custom_rules[]` (local/global rule files)
  - `instructions[]` (from config URLs/globs/files)
  - `sdk_user_system_prompt` (explicit `OpenAgenticOptions.system_prompt`)

Default output order must match OpenCode. We can add an optional "strict" mode that enforces exact ordering.

### Security Model

- URL instruction fetch must be gated:
  - default: allow only `https://` (optionally allow http via config)
  - enforce timeout (5s) and max bytes
  - optionally allowlist domains
- File instruction loading must:
  - be deterministic
  - avoid following symlinks by default (configurable)
  - cap file size

### Edge Cases

- Missing rule files: skip silently.
- Malformed URLs / fetch failures: treat as empty instruction.
- Relative instructions when project discovery disabled and no `OPENCODE_CONFIG_DIR`: warn + skip.

## TDD (Acceptance Tests)

Prompt selection + env + rules/instructions:

- `tests/test_opencode_prompt_system_parity.py`
  - environment block includes `Working directory`, git detection, `Platform`, and date
  - local rule files stop at the first matching kind (AGENTS > CLAUDE > CONTEXT) but include multiple
    matches of that kind across ancestors
  - global rule file stops at the first existing candidate
  - URL instructions are included only when fetch returns non-empty; fetch uses timeout 5s
  - anthropic provider header + claude-model provider prompt selection

Codex/OAuth wiring:

- `tests/test_codex_prompt_wiring.py`
  - Responses `instructions` is set
  - system content is sent as a `role: user` message in Codex sessions
