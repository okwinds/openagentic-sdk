# OpenCode Parity v2 — Providers + Models

## Source of Truth (OpenCode)

- Provider layer: `/mnt/e/development/opencode/packages/opencode/src/provider/*`
- Models.dev integration: `/mnt/e/development/opencode/packages/opencode/src/provider/models` (and `ModelsDev` usage)
- Config integration: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Prompt headers per provider/model: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`

## Parity Target

OpenCode’s provider system is not just "call a model":

- Provider registry + auth store.
- Model listing + variants.
- Per-model token limits used by compaction.
- Provider-specific prompt headers and safety affordances.

## Current State (openagentic-sdk)

- Providers exist (Responses + compatible) and we added adapter aliases for Anthropic/Gemini/Qwen.
- Provider registry exists.
- Config-defined models/variants exist (partial).

Major missing/incorrect vs OpenCode:

- No models.dev backed authoritative model metadata (limits/variants).
- No unified auth storage per provider.
- Prompt header integration is incomplete.

## Plan

- Implement provider auth store parity:
  - per-provider tokens/keys
  - secure file permissions
  - CLI management commands

- Implement model metadata parity:
  - limits (context/input/output)
  - variants
  - search/suggestions

- Integrate with prompt system and compaction:
  - model limits drive overflow math
  - provider prompt templates are selected by model id patterns

## Security

- Never persist raw API keys in logs.
- Add redaction in debug output.

## TDD

- Provider contract tests:
  - streaming
  - tool calls
  - usage totals
- Model metadata tests:
  - limit math
  - variant selection
