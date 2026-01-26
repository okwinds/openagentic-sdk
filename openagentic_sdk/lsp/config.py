from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


# Built-in LSP server ids from OpenCode's registry:
# /mnt/e/development/opencode/packages/opencode/src/lsp/server.ts
BUILTIN_LSP_SERVER_IDS: set[str] = {
    "deno",
    "typescript",
    "vue",
    "eslint",
    "oxlint",
    "biome",
    "gopls",
    "ruby-lsp",
    "ty",
    "pyright",
    "elixir-ls",
    "zls",
    "csharp",
    "fsharp",
    "sourcekit-lsp",
    "rust",
    "clangd",
    "svelte",
    "astro",
    "jdtls",
    "kotlin-ls",
    "yaml-ls",
    "lua-ls",
    "php intelephense",
    "prisma",
    "dart",
    "ocaml-lsp",
    "bash",
    "terraform",
    "texlab",
    "dockerfile",
    "gleam",
    "clojure-lsp",
    "nixd",
    "tinymist",
    "haskell-language-server",
}


@dataclass(frozen=True, slots=True)
class LspServerConfig:
    """OpenCode-compatible LSP server config."""

    server_id: str
    command: Sequence[str]
    extensions: Sequence[str] = ()
    disabled: bool = False
    env: Mapping[str, str] | None = None
    initialization: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class LspConfig:
    enabled: bool
    servers: Sequence[LspServerConfig] = ()


def _as_str_list_nonempty(v: Any) -> list[str] | None:
    if not isinstance(v, list) or not v:
        return None
    out: list[str] = []
    for x in v:
        if not isinstance(x, str) or not x:
            return None
        out.append(x)
    return out


def _as_str_list_allow_empty(v: Any) -> list[str] | None:
    if not isinstance(v, list):
        return None
    out: list[str] = []
    for x in v:
        if not isinstance(x, str) or not x:
            return None
        out.append(x)
    return out


def _as_str_dict(v: Any) -> dict[str, str] | None:
    if not isinstance(v, dict):
        return None
    out: dict[str, str] = {}
    for k, val in v.items():
        if not isinstance(k, str):
            continue
        if isinstance(val, str):
            out[k] = val
    return out


def parse_lsp_config(cfg: Mapping[str, Any] | None) -> LspConfig:
    """Parse OpenCode-style `lsp` config.

    OpenCode schema (simplified):

    - lsp: false | { [id]: { command: string[], extensions?: string[], disabled?: bool, env?: {..}, initialization?: {..} } | { disabled: true } }
    """

    if not isinstance(cfg, Mapping):
        return LspConfig(enabled=True, servers=())

    raw = cfg.get("lsp")
    if raw is False:
        return LspConfig(enabled=False, servers=())
    if raw is None:
        return LspConfig(enabled=True, servers=())

    if not isinstance(raw, Mapping):
        return LspConfig(enabled=True, servers=())

    servers: list[LspServerConfig] = []
    for server_id, spec in raw.items():
        if not isinstance(server_id, str) or not server_id:
            continue
        if not isinstance(spec, Mapping):
            continue

        disabled = bool(spec.get("disabled", False))
        if disabled is True and "command" not in spec:
            # Matches the OpenCode shape: { disabled: true }.
            servers.append(LspServerConfig(server_id=server_id, command=(), disabled=True))
            continue

        cmd = _as_str_list_nonempty(spec.get("command"))
        if cmd is None:
            raise ValueError(f"lsp: server '{server_id}' missing valid command")

        exts_present = "extensions" in spec
        exts = _as_str_list_allow_empty(spec.get("extensions")) if exts_present else None

        # OpenCode parity: for custom LSP servers (ids not in built-in registry),
        # an extensions array is required.
        if (server_id not in BUILTIN_LSP_SERVER_IDS) and (not disabled) and exts is None:
            raise ValueError(f"lsp: custom server '{server_id}' requires 'extensions'")

        env = _as_str_dict(spec.get("env"))
        init = spec.get("initialization")
        init2 = dict(init) if isinstance(init, Mapping) else None

        servers.append(
            LspServerConfig(
                server_id=server_id,
                command=cmd,
                extensions=exts or (),
                disabled=disabled,
                env=env,
                initialization=init2,
            )
        )

    return LspConfig(enabled=True, servers=servers)
