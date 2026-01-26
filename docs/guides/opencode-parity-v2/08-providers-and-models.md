# OpenCode Parity v2-08: Providers + Models

This repo now includes an OpenCode-like provider/model surface:

- Models.dev-style model metadata cache (`models.json`).
- `provider/model` selection in config (`opencode.json{c}`).
- Provider auth storage (`auth.json`) + CLI management commands.
- Server routes for provider listing and auth surface.

## Model Selection: `provider/model`

OpenCode config uses `provider/model` strings (split on the first `/`). Example:

```json
{
  "model": "openrouter/openai/gpt-5-chat",
  "provider": {
    "openrouter": {
      "options": {
        "baseURL": "https://example.invalid",
        "apiKey": "..."
      }
    }
  }
}
```

In OpenAgentic SDK:

- `openagentic_cli/config.py` resolves `config.model` into:
  - a concrete provider object
  - a model id (without the provider prefix)
  - an API key (from config/auth/env)

## Models.dev Metadata

OpenCode uses models.dev to get authoritative model metadata (limits, variants, headers, etc).

In this repo:

- `openagentic_sdk/providers/models_dev.py` loads models metadata from:
  1) cache file: `~/.openagentic-sdk/cache/models.json`
  2) optional embedded snapshot (if present)
  3) network fetch: `${OPENCODE_MODELS_URL:-https://models.dev}/api.json` (unless disabled)

Environment flags:

- `OPENCODE_DISABLE_MODELS_FETCH=1` disables network fetching.
- `OPENCODE_MODELS_URL=https://models.dev` overrides the base URL.
- `OPENCODE_ENABLE_EXPERIMENTAL_MODELS=1` includes alpha models.

## Compaction Uses Model Limits

When `config.model` is `provider/model` and the user did not specify explicit compaction limits,
the CLI derives:

- `CompactionOptions.context_limit` from `model.limit.context`
- `CompactionOptions.output_limit` from `model.limit.output`

This matches OpenCode’s behavior where compaction is driven by model metadata.

## Provider Auth Store + CLI

The provider auth schema matches OpenCode (`auth.json`) and is stored under:

- `~/.openagentic-sdk/auth.json`

CLI helpers:

- `oa auth set <provider_id> --key <api_key>`
- `oa auth remove <provider_id>`
- `oa auth list`

Notes:

- Keys are stored with best-effort file permissions (`0600`).
- Commands avoid echoing secrets.

## Server Routes

The local server exposes an OpenCode-like provider surface:

- `GET /provider` returns `{all, default, connected}`.
- `GET /provider/auth` returns available auth method shapes.
- `POST /provider/:providerID/oauth/authorize` and `/oauth/callback` exist but are currently stubbed as unsupported.
