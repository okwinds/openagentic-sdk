# OpenCode Parity v2 — Providers + Models

## Source of Truth (OpenCode)

- Provider layer: `/mnt/e/development/opencode/packages/opencode/src/provider/*`
- Models.dev integration: `/mnt/e/development/opencode/packages/opencode/src/provider/models` (and `ModelsDev` usage)
- Config integration: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Prompt headers per provider/model: `/mnt/e/development/opencode/packages/opencode/src/session/system.ts`

Key server routes:

- `/mnt/e/development/opencode/packages/opencode/src/server/routes/provider.ts`
  - `GET /provider`
  - `GET /provider/auth`
  - `POST /provider/:providerID/oauth/authorize`
  - `POST /provider/:providerID/oauth/callback`

## Parity Target

OpenCode’s provider system is not just "call a model":

- Provider registry + auth store.
- Model listing + variants.
- Per-model token limits used by compaction.
- Provider-specific prompt headers and safety affordances.

In particular, OpenCode resolves model refs as `provider/model`:

- `config.model` is a string like `anthropic/claude-2`.
- Providers can be enabled/disabled via `enabled_providers` and `disabled_providers`.

## Current State (openagentic-sdk)

- Providers exist (Responses + compatible) and we added adapter aliases for Anthropic/Gemini/Qwen.
- Provider registry exists.
- Config-defined models/variants exist (partial).

What exists today (but not wired end-to-end):

- Provider auth storage schema already matches OpenCode: `openagentic_sdk/auth.py` (`auth.json`).
- Compaction overflow math is implemented, but is driven by `CompactionOptions.context_limit` rather than per-model limits.

Major missing/incorrect vs OpenCode:

- No models.dev backed authoritative model metadata (limits/variants).
- No unified auth storage per provider.
- Prompt header integration is incomplete.

Notes from OpenCode reference implementation:

- `ModelsDev` loads providers+models from:
  - cached JSON: `${Global.Path.cache}/models.json`
  - optional build snapshot: `./models-snapshot` (if present)
  - else fetch: `https://models.dev/api.json` (or `OPENCODE_MODELS_URL`), unless disabled.
- `Provider` merges:
  - models.dev database
  - config overrides: `config.provider[providerID]` (name/env/options/models.variants)
  - auth store: `Auth.get(providerID)` (api key or oauth tokens)
  - env vars listed in provider metadata (`env[]`).
- Model filtering:
  - drop deprecated models
  - alpha models gated by `OPENCODE_ENABLE_EXPERIMENTAL_MODELS`
  - provider-level whitelist/blacklist
  - merge + drop disabled variants.

## Plan

This is implemented as a thin "provider+model resolution" layer outside the runtime:

1) Models.dev-style catalog (authoritative model metadata)

- Add `openagentic_sdk/providers/models_dev.py`:
  - cache path: `~/.openagentic-sdk/cache/models.json` (via `default_session_root()`)
  - load order: cache -> optional snapshot -> network fetch
  - env flags:
    - `OPENCODE_MODELS_URL` (override base, default `https://models.dev`)
    - `OPENCODE_DISABLE_MODELS_FETCH` (disable network)
- Schema validation is best-effort, tolerant of unknown fields.

2) Provider/model resolution

- Add `openagentic_sdk/providers/selection.py`:
  - parse `model` as `provider/model` (split on first `/` only; model IDs may contain `/`).
  - resolve `(provider_obj, api_key, model_id, model_limits, model_headers)` via:
    - config `provider.<id>.options` (baseURL/apiKey/timeout/etc)
    - `auth.json` (`openagentic_sdk/auth.py`) for per-provider keys/tokens
    - env vars listed by models.dev provider metadata

3) Compaction integration

- Derive effective compaction limits from model metadata when the caller did not set them:
  - if `CompactionOptions.context_limit == 0`, use `model.limit.context`
  - if `CompactionOptions.output_limit is None`, use `model.limit.output`
- Apply these derived limits inside `openagentic_sdk/runtime.py` when checking `would_overflow()`.

4) Server surface parity

- Implement routes in `openagentic_sdk/server/http_server.py`:
  - `GET /provider` -> `{ all, default, connected }`
  - `GET /provider/auth` -> `{ [providerID]: [{type,label}] }`
  - `POST /provider/:providerID/oauth/authorize` and `/oauth/callback` (phase 1: explicit unsupported unless implemented)
- Ensure all responses redact secrets.

5) CLI surface parity

- Add `oa models` (list models; `--refresh` to refresh cache).
- Extend option building so `config.model="provider/model"` selects provider and model id correctly.

## Security

- Never persist raw API keys in logs.
- Add redaction in debug output.
- Models.dev fetch is optional and must have timeouts and response size caps.
- Provider auth files must be `0600` best-effort and must not be served verbatim.

## TDD

- Provider contract tests:
  - streaming
  - tool calls
  - usage totals
- Model metadata tests:
  - limit math
  - variant selection

Additional acceptance tests for v2-08:

- `provider/model` parsing (including model IDs containing `/`).
- Compaction derived limits (context/output) drive overflow behavior without manual config.
- Server `/provider` surfaces `enabled_providers`/`disabled_providers` filtering.
- Server `/provider` never leaks `apiKey`/tokens.
