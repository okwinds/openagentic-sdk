# Parity 02: Config System (opencode.json parity)

Status: implemented (initial slice) in this repo:

- Config discovery (global + project + .opencode), deterministic precedence/merge
- JSONC comment stripping + trailing comma removal
- Substitutions: `{env:VAR}` and `{file:path}` (file path relative to config file)
- CLI integration (loads config automatically when present)
- Tests

Key files:

- `openagentic_sdk/opencode_config.py`
- `openagentic_cli/config.py`
- `tests/test_opencode_config_loader.py`

## Analysis

OpenCode config provides:

- Precedence and merge across multiple locations, including `.opencode/`.
- JSON/JSONC support.
- Variable substitution `{env:VAR}`, `{file:path}`.
- Config-driven: providers/models, instructions, plugins, commands, permissions, compaction settings, etc.

References:

- `opencode/packages/opencode/src/config/config.ts`
- Docs: `opencode/packages/web/src/content/docs/config.mdx`

Current repo relies on `OpenAgenticOptions` + env; no file config loader.

## Plan

### Deliverables

- Implement a Python config loader that can read and merge:
  - project-level `opencode.json` / `opencode.jsonc`
  - project-level `.opencode/opencode.json{,c}`
  - global config under `~/.config/opencode/` equivalents (configurable root)
- Implement JSONC parsing (comment stripping).
- Implement substitutions `{env:}`, `{file:}`.

### Integration

- CLI: load config by default; SDK: opt-in via `setting_sources` or explicit `config_path`.

### Acceptance Criteria

- Unit tests for precedence, JSONC parsing, substitutions.

## TDD

- Build fixtures in `tests/` that simulate config file trees.
