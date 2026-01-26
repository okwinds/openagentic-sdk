# Parity 10: Providers + Models (Provider-Agnostic Layer)

## Analysis

OpenCode provider layer supports multiple providers and model listing/variants, with auth flows.

References:

- `opencode/packages/opencode/src/provider/provider.ts`
- `opencode/packages/opencode/src/provider/auth.ts`

Current repo supports OpenAI Responses and OpenAI-compatible only.

## Plan

- Add provider abstraction parity:
  - model registry + listing
  - provider auth storage
  - per-provider system prompt header integration
- Implement at least Anthropic/Gemini/Qwen equivalents (or adapters) to match OpenCode behavior.

## TDD

- Provider contract tests (non-stream + stream + tool calls + usage metadata).
