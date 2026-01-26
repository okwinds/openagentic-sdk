# OpenCode Parity v2 — Roadmap, Acceptance Criteria, Security Model, Test Strategy

Goal: implement **full OpenCode behavioral parity** (no “minimal slice”), while adding **optional** hardening and correctness improvements that do not regress parity.

This file is the execution contract: feature matrix + acceptance criteria + security model + test strategy.

OpenCode source-of-truth (local): `/mnt/e/development/opencode`

## Parity Principles

1) OpenCode code is the primary truth.

- When docs disagree with code, match code first; treat doc drift as a noted discrepancy.

2) "Better than OpenCode" must be **additive and optional**.

- We will implement strict parity behavior.
- We may add a hardened mode (extra guards, stricter defaults) but it must be explicit and testable.

3) Determinism is mandatory.

- Stable ordering for discovery results.
- Stable serialization formats.

4) Security is mandatory and explicit.

- Dangerous operations require explicit enablement + clear audit trail.
- Credential stores must not leak secrets.

## Feature Matrix (Acceptance Criteria)

Each area is considered DONE only when its acceptance criteria are met and tests exist.

### A) Prompt System + Rules

Acceptance criteria:

- Prompt assembly order matches OpenCode (`header` + base prompt + `input.system` + `input.user.system`).
- Provider/model prompt selection matches OpenCode string rules.
- Anthropic provider header spoof matches OpenCode behavior.
- `SystemPrompt.environment()` equivalent block exists and is injected in the correct place.
- Rule discovery parity:
  - local rule filename priority and early-stop behavior
  - global rule filename priority and early-stop behavior
- `config.instructions` parity:
  - supports URL fetch with timeout and failure-to-empty behavior
  - supports relative glob-up resolution
  - supports absolute-path basename glob behavior
- Codex/OAuth special-case:
  - uses Responses `instructions` field
  - system is sent as a user message for that path

Tests:

- Unit tests for selection and discovery.
- Integration tests for final assembled prompt blocks.

Security (baseline parity + optional hardening):

- Parity mode: behave like OpenCode.
- Hardened mode: enforce HTTPS-only by default for URL instructions, cap bytes, optional domain allowlist.

### B) Config System

Acceptance criteria:

- Full precedence layers:
  - remote well-known config (Auth-backed)
  - global config (XDG)
  - `OPENCODE_CONFIG`
  - project `opencode.jsonc` then `opencode.json` with correct local precedence
  - `OPENCODE_CONFIG_CONTENT`
  - directory-pack scanning (`.opencode` up-tree, `~/.opencode`, `OPENCODE_CONFIG_DIR`)
- Merge semantics match OpenCode:
  - deep merge objects
  - only `plugin` and `instructions` concatenate/dedupe
  - plugin canonical-name dedupe keeps higher precedence
- JSONC parsing errors are annotated (line/column, failing line).
- Substitutions match OpenCode:
  - `{env:VAR}`
  - `{file:path}` with `~/` expansion, relative-to-config-dir, missing-file error, commented-token skip, JSON string-literal escaping
- `$schema` insertion behavior matches OpenCode (including write-back behavior decision).

Tests:

- Contract tests for precedence, merge semantics, substitutions.
- Regression tests for docs-vs-code discrepancy (inline config vs directory-pack override).

Security:

- Hardened mode should redact substitution expansions in error output.

### C) Commands

Acceptance criteria:

- Command sources match OpenCode:
  - built-ins
  - config `command` entries
  - markdown commands `{command,commands}/**/*.md` in config directories
  - MCP prompts as commands
- Markdown command name derivation matches OpenCode (nested path preserved).
- Runtime expansion matches OpenCode:
  - args tokenization (quotes, `[Image N]`)
  - `$N` substitution with max-placeholder swallowing remainder
  - `$ARGUMENTS` (multiline)
  - implicit arg appending when template has no placeholders
  - shell `!`cmd`` semantics
  - `@file` -> attachment parts and `@agent` fallback
  - subtask behavior parity (file parts dropped)

Tests:

- Unit tests for tokenizer and placeholder semantics.
- Integration tests for command rendering end-to-end.

Security:

- Parity mode: match OpenCode semantics.
- Hardened mode: require explicit permission gating for shell expansion and external file attachment expansion.

### D) Plugins + Custom Tools

Acceptance criteria:

- Directory-pack scanning parity: `.opencode` up-tree, `~/.opencode`, `OPENCODE_CONFIG_DIR`.
- Plugin list load parity.
- Plugin dedupe parity.
- Clear provenance labels for tools/plugins.

Tests:

- Ordering and precedence tests.
- Safety tests for default deny / opt-in behaviors.

### E) MCP

Acceptance criteria:

- Transport parity: StreamableHTTP + SSE fallback.
- OAuth parity:
  - local callback server
  - PKCE verifier and OAuth state
  - dynamic client registration
  - token refresh handling
  - URL-bound credential validation
  - secure file permissions (0600 equivalent)
- Prompts/resources parity:
  - tool wrappers exist
  - prompts are also exposed as commands where appropriate

Tests:

- OAuth storage and URL-binding tests.
- Mock OAuth server integration tests.

### F) Compaction

Acceptance criteria:

- Overflow detection math uses model limits and OUTPUT_TOKEN_MAX behavior.
- Prune algorithm matches OpenCode thresholds and traversal stop conditions.
- Hard compaction:
  - marker question parity
  - summary pivot filtering parity
  - plugin hook parity (`experimental.session.compacting`)
  - auto-continue message parity

Tests:

- Unit tests for math/traversal.
- Integration tests that simulate overflow and verify pivot+prune results.

### G) Sessions

Acceptance criteria:

- Timeline controls parity (undo/redo/head).
- Fork/children parity.
- Share/unshare parity.
- Todo persistence + server surface.
- Snapshot/revert parity if OpenCode exposes it.

### H) Providers + Models

Acceptance criteria:

- Provider auth store parity.
- Model metadata parity (limits, variants) used by compaction.
- Prompt integration parity (provider headers + model selection).

### I) Server + Clients (CLI/TUI)

Acceptance criteria:

- Server routes parity for sessions/messages/status/todo/share/summarize/stream.
- Auth and request-size limits.
- CLI parity commands to manage server, sessions, config, providers, MCP auth.
- TUI parity features (session list, streaming, tool approvals, todo list, command palette).

## Test Strategy

We will maintain three layers:

1) Unit tests: parsing, merge semantics, templating, math.
2) Contract tests: filesystem discovery, precedence ordering, stable outputs.
3) Integration tests: server endpoints, streaming behavior, OAuth flows.

Guidelines:

- Hermetic by default (temp dirs, fixtures; no network unless explicitly mocked).
- Deterministic ordering.
- Explicitly label pre-existing failures vs new failures.

## Security Model (Cross-Cutting)

Threat surfaces:

- Remote config (`/.well-known/opencode`) and URL instructions.
- Command shell expansion.
- Plugin/custom tool loading.
- MCP OAuth tokens and credentials.
- Server endpoints.

Required controls:

- Secret redaction in logs/errors.
- Timeouts and size caps for all IO.
- Strict file permissions for credential storage.
- Explicit allowlists / opt-in for remote sources.
