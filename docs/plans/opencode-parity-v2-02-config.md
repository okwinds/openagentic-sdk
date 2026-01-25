# OpenCode Parity v2 — Config System

## Source of Truth (OpenCode)

- Config loader: `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`
- Config docs: `/mnt/e/development/opencode/packages/web/src/content/docs/config.mdx` (if present)

## OpenCode Behavior (Detailed)

### 1) Config precedence layers

OpenCode merges config in this precedence order (lowest to highest):

1. Remote well-known config from auth entries where `type === "wellknown"`:
   - fetched from `${origin}/.well-known/opencode`
2. Global user config
3. Explicit config file from `OPENCODE_CONFIG`
4. Project config (unless `OPENCODE_DISABLE_PROJECT_CONFIG`):
   - finds `opencode.jsonc` then `opencode.json` upward
   - loads from root -> leaf (using `found.toReversed()`)
5. Inline config content from `OPENCODE_CONFIG_CONTENT`

Reference: `Config.state` in `config.ts`

Docs-vs-code note:

- OpenCode docs claim inline config is last/highest precedence, but the OpenCode code applies inline config *before* directory-pack scanning (which merges afterward and can override inline). For parity we must follow OpenCode code behavior.

### 2) Directory scanning for additional config + content

OpenCode then builds a `directories` list (deduped):

- `${Global.Path.config}`
- All `.opencode` dirs upward from project (only if project discovery enabled)
- `~/.opencode` (always)
- `${OPENCODE_CONFIG_DIR}` (if set)

For each directory, OpenCode:

- Loads `opencode.jsonc/json` when the directory ends in `.opencode` or equals `OPENCODE_CONFIG_DIR`.
- Ensures `node_modules` exists and installs dependencies (bun):
  - writes `package.json` + `.gitignore` if missing
  - installs `@opencode-ai/plugin@<version>`
  - runs `bun install`
- Loads and merges:
  - commands from `{command,commands}/**/*.md`
  - agents and modes
  - plugins list

Reference: directory loop in `Config.state`.

Important: directory-pack scanning currently runs *after* `OPENCODE_CONFIG_CONTENT` is applied, so `.opencode` directories can override inline config despite comments/docs implying the opposite.

### 3) Merge semantics

OpenCode uses deep-merge for objects, with special handling:

- `plugin[]` concatenates and de-duplicates.
- `instructions[]` concatenates and de-duplicates.

Other list fields follow the default deep-merge semantics (do not assume concat).

Reference: `mergeConfigConcatArrays()`

Plugin dedupe has an additional step:

- OpenCode de-duplicates plugins by a canonicalized "plugin name" and uses "later wins" (higher-precedence) behavior.
- This is separate from the earlier Set-based exact-string dedupe.

Reference: plugin canonicalization + dedupe in `/mnt/e/development/opencode/packages/opencode/src/config/config.ts`.

### 4) JSONC parsing + helpful error reporting

- Parses JSONC with trailing comma support.
- On parse errors, it reports line/column and prints the failing line.

Reference: `parseJsonc(...)` usage.

### 5) Substitutions

- `{env:VAR}` replaced with env var or empty.
- `{file:path}` replaced with file content:
  - resolves relative to the config file directory
  - supports `~/` expansion
  - errors if missing
  - skips replacement if the line is commented out (`// ...`)
  - escapes newlines/quotes to embed as a JSON string literal.

Reference: `load(text, configFilepath)`.

Edge case worth matching (and testing): OpenCode decides whether to skip a `{file:...}` substitution based on the first line that contains the token, so repeated tokens can behave unexpectedly if one occurrence is commented.

### 6) Schema auto-insertion

- If `$schema` is missing after successful parse, OpenCode sets it to `https://opencode.ai/config.json`.
- It attempts to write it back into the original file while preserving `{env:VAR}` strings.

Reference: `$schema` insertion in `load()`.

### 7) Migrations / compatibility fields

OpenCode migrates or normalizes:

- `mode` -> `agent` (deprecated)
- legacy top-level `tools` -> `permission` rules
- `autoshare: true` -> `share = "auto"`

## Current State (openagentic-sdk)

- Loader exists: `openagentic_sdk/opencode_config.py`

Implemented (close to OpenCode behavior):

- Full precedence layers:
  - remote well-known config (`/.well-known/opencode`) from `WellKnownAuth` entries: `openagentic_sdk/opencode_config.py` (`load_state`)
  - global config (XDG `~/.config/opencode`): `openagentic_sdk/opencode_config.py` (`_xdg_config_dir`, `_load_global_config`)
  - `OPENCODE_CONFIG` path override
  - project config discovery (up-tree) unless `OPENCODE_DISABLE_PROJECT_CONFIG`
  - inline config via `OPENCODE_CONFIG_CONTENT`
  - directory packs (after inline): global dir + up-tree `.opencode` + `~/.opencode` + `OPENCODE_CONFIG_DIR`
- Merge semantics: only `plugin` and `instructions` concatenate; all other arrays are replaced.
- Plugin canonicalization + later-wins dedupe (matches OpenCode `deduplicatePlugins`).
- JSONC parsing with helpful parse errors (line/column + failing line).
- Substitutions:
  - `{env:VAR}`
  - `{file:path}` with relative-to-config-dir resolution, `~/` expansion, missing-file errors,
    commented-line skip, and JSON string-literal escaping.
- `$schema` auto-insertion with best-effort write-back.
- Directory-pack loaders:
  - `{command,commands}/**/*.md` via minimal frontmatter parser
  - `{agent,agents}/**/*.md`
  - `{mode,modes}/*.md` merged into `agent`
  - `{plugin,plugins}/*.{ts,js}` recorded as `file://...`

Evidence (tests in this repo):

- `tests/test_opencode_config_loader.py`
- `tests/test_opencode_config_wellknown.py`
- `tests/test_opencode_config_precedence_and_packs.py`

Remaining gaps vs OpenCode:

- Dependency installation for directory packs (bun + `@opencode-ai/plugin`) is not implemented (must be permission-gated).
- Remote well-known config error semantics differ (OpenCode throws on non-OK; this repo currently treats fetch failures as empty).
- Path handling differs in some corners (OpenCode uses Bun.Glob + followSymlinks + dot semantics; this repo implements a deterministic walk with followlinks=True).

## Security Notes (Parity + Better-than-OpenCode)

OpenCode parse errors include the post-substitution JSONC text; that can leak expanded `{env:...}` and `{file:...}` secrets into logs/errors.

For our parity implementation:

- Redact substitution values in error output (keep the variable reference).
- For `{file:...}`, include the resolved path in errors but never include file content.
- Gate remote well-known config fetch behind explicit opt-in, enforce HTTPS + strict timeout + max bytes.

## Plan (No-Compromise Implementation)

### Target: parity-level loader + indexing

- Implement full precedence layers including well-known remote config.
- Implement directory scanning behavior:
  - `.opencode` directories up-tree, `~/.opencode`, `OPENCODE_CONFIG_DIR`.
  - Load markdown-defined commands/agents/modes/plugins.

### Security Model

- Remote config fetch:
  - strict timeouts
  - HTTPS by default
  - size limits
  - cache with etag/last-modified when possible
- Dependency installation:
  - must be opt-in and permission-gated (network + execution)
  - run in isolated environment (prefer uv/pip with constraints)

### Tests

- Precedence tests covering all layers.
- Merge semantics tests (plugin/instructions concat only).
- Substitution tests matching OpenCode quoting + missing-file errors.
- Directory scanning tests for `.opencode` command discovery.
