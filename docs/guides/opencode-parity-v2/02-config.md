# v2-02 Config System

This guide describes how to configure the SDK using OpenCode-style config files and directory packs.

## Where Config Comes From

The config loader merges multiple layers (lowest to highest precedence):

1) Remote well-known config (`/.well-known/opencode`) from auth entries of type "wellknown".
2) Global user config (XDG): `~/.config/opencode/`.
3) Explicit config file via `OPENCODE_CONFIG`.
4) Project config (unless `OPENCODE_DISABLE_PROJECT_CONFIG`):
   - searches upward for `opencode.jsonc`, then `opencode.json`.
   - loads from root -> leaf.
5) Inline config via `OPENCODE_CONFIG_CONTENT`.

Then it scans "config directories" for additional packs (commands/agents/modes/plugins):

- `~/.config/opencode` (global)
- `.opencode/` directories found upward from your project
- `~/.opencode/`
- `${OPENCODE_CONFIG_DIR}` (if set)

## Minimal `opencode.json`

```json
{
  "provider": {
    "openai": {
      "options": {
        "apiKey": "{env:OPENAI_API_KEY}",
        "baseURL": "https://api.openai.com/v1"
      }
    }
  },
  "compaction": {
    "auto": true,
    "prune": true,
    "context_limit": 9000
  }
}
```

## Merge Semantics

- Objects are deep-merged.
- Only these arrays are concatenated and de-duplicated:
  - `plugin`
  - `instructions`
- Most other arrays are replaced by the higher-precedence layer.

Plugins have an extra de-duplication step: canonicalization + "later wins".

## JSONC + Substitutions

Both `opencode.json` and `opencode.jsonc` are supported.

Substitutions:

- `{env:VAR}` expands to the environment variable value or empty.
- `{file:path}` inlines file contents as a JSON string literal.
  - relative paths resolve relative to the config file directory
  - `~/` expands
  - commented-out lines skip substitution

## Directory Packs

Inside any scanned config directory you can place these:

- Commands: `{command,commands}/**/*.md`
- Agents: `{agent,agents}/**/*.md`
- Modes: `{mode,modes}/*.md` (merged into agent)
- Plugins: `{plugin,plugins}/*.{ts,js}` (recorded as `file://...` specs)

In `.opencode/`, this typically looks like:

```
.opencode/
  opencode.json
  commands/
    review.md
  tools/
    my_tool.py
```

## Experimental Flags

Some features are explicitly opt-in for safety:

- JS/TS tools:
  - `opencode.json`: `experimental.js_tools: true`
  - or env: `OA_ENABLE_JS_TOOLS=1`

- JS/TS plugins (file:// only):
  - `opencode.json`: `experimental.js_plugins: true`
  - or env: `OA_ENABLE_JS_PLUGINS=1`

## Useful Env Vars

- `OPENCODE_CONFIG_DIR`: extra global config/pack directory.
- `OPENCODE_CONFIG`: explicit config file path.
- `OPENCODE_CONFIG_CONTENT`: inline JSON/JSONC config string.
- `OPENCODE_DISABLE_PROJECT_CONFIG`: disable project config discovery.
