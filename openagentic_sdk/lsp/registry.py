from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


RootResolver = Callable[[str], str | None]


def _env_flag(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    if v == "":
        return True
    return str(v).strip().lower() not in {"0", "false", "no", "off"}


def _matches_any(dir_path: Path, patterns: list[str]) -> Path | None:
    # Supports both exact filenames and simple globs.
    for pat in patterns:
        if not pat:
            continue
        # If it looks like a glob, try globbing.
        if any(ch in pat for ch in "*?[]"):
            try:
                for m in sorted(dir_path.glob(pat)):
                    return m
            except Exception:  # noqa: BLE001
                continue
        else:
            p = dir_path / pat
            if p.exists():
                return p
    return None


def _nearest_root(
    *,
    workspace_dir: Path,
    file_path: str,
    include: list[str],
    exclude: list[str] | None = None,
    required: bool = False,
) -> str | None:
    """OpenCode-style NearestRoot.

    - Walk upwards from file directory to workspace_dir (inclusive)
    - If any exclude marker is found, return None
    - If include marker is found, return its directory
    - Else return workspace_dir (unless required=True)
    """

    f = Path(file_path)
    start = f.parent
    stop = workspace_dir
    stop = stop.resolve()
    cur = start.resolve()

    def is_under(p: Path, root: Path) -> bool:
        try:
            p.relative_to(root)
            return True
        except Exception:
            return False

    if not is_under(cur, stop):
        # If the file is outside the workspace, OpenCode's tool would deny via
        # permission patterns. Here, we simply refuse.
        return None

    while True:
        if exclude:
            if _matches_any(cur, exclude) is not None:
                return None
        m = _matches_any(cur, include)
        if m is not None:
            return str(cur)
        if cur == stop:
            break
        if cur.parent == cur:
            break
        cur = cur.parent

    if required:
        return None
    return str(stop)


@dataclass(frozen=True, slots=True)
class LspServerDefinition:
    server_id: str
    extensions: list[str]
    root: RootResolver
    command: list[str] | None
    env: Mapping[str, str] | None = None
    initialization: Mapping[str, Any] | None = None


def _workspace_root(workspace_dir: Path) -> RootResolver:
    return lambda _file: str(workspace_dir)


def _root_deno(workspace_dir: Path) -> RootResolver:
    def _r(file_path: str) -> str | None:
        return _nearest_root(
            workspace_dir=workspace_dir,
            file_path=file_path,
            include=["deno.json", "deno.jsonc"],
            exclude=None,
            required=True,
        )

    return _r


def builtin_servers(*, workspace_dir: Path) -> dict[str, LspServerDefinition]:
    """OpenCode-like built-in server registry.

    Security note: this only defines servers. Spawning is handled elsewhere and
    must remain permission-gated.
    """

    ws = workspace_dir.resolve()

    lockfiles = ["package-lock.json", "bun.lockb", "bun.lock", "pnpm-lock.yaml", "yarn.lock"]

    def NR(include: list[str], exclude: list[str] | None = None, *, required: bool = False) -> RootResolver:
        return lambda fp: _nearest_root(workspace_dir=ws, file_path=fp, include=include, exclude=exclude, required=required)

    servers: dict[str, LspServerDefinition] = {}

    servers["deno"] = LspServerDefinition(
        server_id="deno",
        extensions=[".ts", ".tsx", ".js", ".jsx", ".mjs"],
        root=_root_deno(ws),
        command=["deno", "lsp"],
    )

    servers["typescript"] = LspServerDefinition(
        server_id="typescript",
        extensions=[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"],
        root=NR(lockfiles, exclude=["deno.json", "deno.jsonc"]),
        command=["typescript-language-server", "--stdio"],
    )

    servers["vue"] = LspServerDefinition(
        server_id="vue",
        extensions=[".vue"],
        root=NR(lockfiles),
        command=["vue-language-server", "--stdio"],
    )

    servers["eslint"] = LspServerDefinition(
        server_id="eslint",
        extensions=[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue"],
        root=NR(lockfiles),
        # There isn't a ubiquitous single binary; users typically configure this.
        command=["vscode-eslint-language-server", "--stdio"],
    )

    servers["oxlint"] = LspServerDefinition(
        server_id="oxlint",
        extensions=[".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".astro", ".svelte"],
        root=NR([".oxlintrc.json", *lockfiles, "package.json"]),
        command=["oxc_language_server"],
    )

    servers["biome"] = LspServerDefinition(
        server_id="biome",
        extensions=[
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".mjs",
            ".cjs",
            ".mts",
            ".cts",
            ".json",
            ".jsonc",
            ".vue",
            ".astro",
            ".svelte",
            ".css",
            ".graphql",
            ".gql",
            ".html",
        ],
        root=NR(["biome.json", "biome.jsonc", *lockfiles]),
        command=["biome", "lsp-proxy", "--stdio"],
    )

    servers["gopls"] = LspServerDefinition(
        server_id="gopls",
        extensions=[".go"],
        # OpenCode falls back to workspace root when no markers exist.
        root=lambda fp: (
            _nearest_root(workspace_dir=ws, file_path=fp, include=["go.work"], required=False)
            or _nearest_root(workspace_dir=ws, file_path=fp, include=["go.mod", "go.sum"], required=False)
        ),
        command=["gopls"],
    )

    servers["ruby-lsp"] = LspServerDefinition(
        server_id="ruby-lsp",
        extensions=[".rb", ".rake", ".gemspec", ".ru"],
        root=NR(["Gemfile"], required=True),
        command=["rubocop", "--lsp"],
    )

    # Python: OpenCode toggles ty vs pyright. We include both definitions here
    # and filter later.
    servers["ty"] = LspServerDefinition(
        server_id="ty",
        extensions=[".py", ".pyi"],
        root=NR(["pyproject.toml", "ty.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "pyrightconfig.json"]),
        command=["ty", "server"],
    )
    servers["pyright"] = LspServerDefinition(
        server_id="pyright",
        extensions=[".py", ".pyi"],
        root=NR(["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile", "pyrightconfig.json"]),
        command=["pyright-langserver", "--stdio"],
    )

    servers["elixir-ls"] = LspServerDefinition(
        server_id="elixir-ls",
        extensions=[".ex", ".exs"],
        root=NR(["mix.exs", "mix.lock"], required=True),
        command=["elixir-ls"],
    )
    servers["zls"] = LspServerDefinition(
        server_id="zls",
        extensions=[".zig", ".zon"],
        root=NR(["build.zig"], required=True),
        command=["zls"],
    )

    servers["csharp"] = LspServerDefinition(
        server_id="csharp",
        extensions=[".cs"],
        root=NR([".sln", ".csproj", "global.json"]),
        command=["csharp-ls"],
    )
    servers["fsharp"] = LspServerDefinition(
        server_id="fsharp",
        extensions=[".fs", ".fsi", ".fsx", ".fsscript"],
        root=NR([".sln", ".fsproj", "global.json"]),
        command=["fsautocomplete"],
    )

    servers["sourcekit-lsp"] = LspServerDefinition(
        server_id="sourcekit-lsp",
        extensions=[".swift", ".m", ".mm"],
        root=NR(["Package.swift", "*.xcodeproj", "*.xcworkspace"]),
        command=["sourcekit-lsp"],
    )

    # Rust: OpenCode picks workspace root when it finds a Cargo.toml with [workspace].
    def _rust_root(fp: str) -> str | None:
        crate = _nearest_root(workspace_dir=ws, file_path=fp, include=["Cargo.toml", "Cargo.lock"], required=True)
        if crate is None:
            return None
        cur = Path(crate)
        while True:
            p = cur / "Cargo.toml"
            try:
                if p.exists():
                    txt = p.read_text(encoding="utf-8", errors="replace")
                    if "[workspace]" in txt:
                        return str(cur)
            except Exception:  # noqa: BLE001
                pass
            if cur == ws or cur.parent == cur:
                break
            cur = cur.parent
        return crate

    servers["rust"] = LspServerDefinition(
        server_id="rust",
        extensions=[".rs"],
        root=_rust_root,
        command=["rust-analyzer"],
    )

    servers["clangd"] = LspServerDefinition(
        server_id="clangd",
        extensions=[
            ".c",
            ".cpp",
            ".cc",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".hxx",
        ],
        root=NR(["compile_commands.json", "compile_flags.txt", ".clangd", "CMakeLists.txt", "Makefile"]),
        command=["clangd"],
    )

    servers["svelte"] = LspServerDefinition(
        server_id="svelte",
        extensions=[".svelte"],
        root=NR(lockfiles),
        command=["svelteserver", "--stdio"],
    )
    servers["astro"] = LspServerDefinition(
        server_id="astro",
        extensions=[".astro"],
        root=NR(lockfiles),
        command=["astro-ls", "--stdio"],
    )

    servers["jdtls"] = LspServerDefinition(
        server_id="jdtls",
        extensions=[".java"],
        root=NR(["pom.xml", "build.gradle", "build.gradle.kts", ".project", ".classpath"]),
        command=["jdtls"],
    )
    servers["kotlin-ls"] = LspServerDefinition(
        server_id="kotlin-ls",
        extensions=[".kt", ".kts"],
        root=lambda fp: (
            _nearest_root(workspace_dir=ws, file_path=fp, include=["settings.gradle.kts", "settings.gradle"], required=True)
            or _nearest_root(workspace_dir=ws, file_path=fp, include=["gradlew", "gradlew.bat"], required=True)
            or _nearest_root(workspace_dir=ws, file_path=fp, include=["build.gradle.kts", "build.gradle"], required=True)
            or _nearest_root(workspace_dir=ws, file_path=fp, include=["pom.xml"], required=True)
        ),
        command=["kotlin-ls", "--stdio"],
    )
    servers["yaml-ls"] = LspServerDefinition(
        server_id="yaml-ls",
        extensions=[".yaml", ".yml"],
        root=NR(lockfiles),
        command=["yaml-language-server", "--stdio"],
    )
    servers["lua-ls"] = LspServerDefinition(
        server_id="lua-ls",
        extensions=[".lua"],
        root=NR([".luarc.json", ".luarc.jsonc", ".luacheckrc", ".stylua.toml", "stylua.toml", "selene.toml", "selene.yml"]),
        command=["lua-language-server"],
    )
    servers["php intelephense"] = LspServerDefinition(
        server_id="php intelephense",
        extensions=[".php"],
        root=NR(["composer.json", "composer.lock", ".php-version"]),
        command=["intelephense", "--stdio"],
    )
    servers["prisma"] = LspServerDefinition(
        server_id="prisma",
        extensions=[".prisma"],
        root=NR(["schema.prisma", "prisma/schema.prisma", "prisma"], exclude=["package.json"]),
        command=["prisma", "language-server"],
    )
    servers["dart"] = LspServerDefinition(
        server_id="dart",
        extensions=[".dart"],
        root=NR(["pubspec.yaml", "analysis_options.yaml"]),
        command=["dart", "language-server", "--lsp"],
    )
    servers["ocaml-lsp"] = LspServerDefinition(
        server_id="ocaml-lsp",
        extensions=[".ml", ".mli"],
        root=NR(["dune-project", "dune-workspace", ".merlin", "opam"]),
        command=["ocamllsp"],
    )

    servers["bash"] = LspServerDefinition(
        server_id="bash",
        extensions=[".sh", ".bash", ".zsh", ".ksh"],
        root=_workspace_root(ws),
        command=["bash-language-server", "start"],
    )
    servers["terraform"] = LspServerDefinition(
        server_id="terraform",
        extensions=[".tf", ".tfvars"],
        root=NR([".terraform.lock.hcl", "terraform.tfstate", "*.tf"]),
        command=["terraform-ls", "serve"],
    )
    servers["texlab"] = LspServerDefinition(
        server_id="texlab",
        extensions=[".tex", ".bib"],
        root=NR([".latexmkrc", "latexmkrc", ".texlabroot", "texlabroot"]),
        command=["texlab"],
    )
    servers["dockerfile"] = LspServerDefinition(
        server_id="dockerfile",
        extensions=[".dockerfile", "Dockerfile"],
        root=_workspace_root(ws),
        command=["docker-langserver", "--stdio"],
    )

    servers["gleam"] = LspServerDefinition(
        server_id="gleam",
        extensions=[".gleam"],
        root=NR(["gleam.toml"]),
        command=["gleam", "lsp"],
    )
    servers["clojure-lsp"] = LspServerDefinition(
        server_id="clojure-lsp",
        extensions=[".clj", ".cljs", ".cljc", ".edn"],
        root=NR(["deps.edn", "project.clj", "shadow-cljs.edn", "bb.edn", "build.boot"]),
        command=["clojure-lsp", "listen"],
    )
    servers["nixd"] = LspServerDefinition(
        server_id="nixd",
        extensions=[".nix"],
        root=lambda fp: (
            _nearest_root(workspace_dir=ws, file_path=fp, include=["flake.nix"], required=True) or str(ws)
        ),
        command=["nixd"],
    )
    servers["tinymist"] = LspServerDefinition(
        server_id="tinymist",
        extensions=[".typ", ".typc"],
        root=NR(["typst.toml"]),
        command=["tinymist"],
    )
    servers["haskell-language-server"] = LspServerDefinition(
        server_id="haskell-language-server",
        extensions=[".hs", ".lhs"],
        root=NR(["stack.yaml", "cabal.project", "hie.yaml", "*.cabal"]),
        command=["haskell-language-server-wrapper", "--lsp"],
    )

    return servers


def build_server_registry(*, cfg: Mapping[str, Any] | None, workspace_dir: Path) -> tuple[bool, dict[str, LspServerDefinition]]:
    """Build enabled servers by merging built-ins with config overrides."""

    # cfg.lsp === false disables.
    if isinstance(cfg, Mapping) and cfg.get("lsp") is False:
        return False, {}

    servers = builtin_servers(workspace_dir=workspace_dir)

    # Experimental toggle: ty vs pyright.
    if _env_flag("OPENCODE_EXPERIMENTAL_LSP_TY"):
        servers.pop("pyright", None)
    else:
        servers.pop("ty", None)

    raw = cfg.get("lsp") if isinstance(cfg, Mapping) else None
    if isinstance(raw, Mapping):
        for sid, spec in raw.items():
            if not isinstance(sid, str) or not sid:
                continue
            if not isinstance(spec, Mapping):
                continue
            if bool(spec.get("disabled")) and "command" not in spec:
                # Disable built-in.
                servers.pop(sid, None)
                continue
            cmd = spec.get("command")
            if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
                # Invalid: skip (validation should be done earlier).
                continue
            exts = spec.get("extensions")
            exts2: list[str] | None
            if isinstance(exts, list) and all(isinstance(x, str) and x for x in exts):
                exts2 = [str(x) for x in exts]
            else:
                exts2 = None
            env = spec.get("env")
            env2 = {str(k): str(v) for k, v in env.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(env, Mapping) else None
            init = spec.get("initialization")
            init2 = dict(init) if isinstance(init, Mapping) else None

            existing = servers.get(sid)
            root_fn = existing.root if existing is not None else (lambda _fp: str(workspace_dir.resolve()))
            merged_exts = exts2 if exts2 is not None else (existing.extensions if existing is not None else [])
            servers[sid] = LspServerDefinition(
                server_id=sid,
                extensions=list(merged_exts),
                root=root_fn,
                command=[str(x) for x in cmd],
                env=env2 or (existing.env if existing is not None else None),
                initialization=init2 or (existing.initialization if existing is not None else None),
            )

    return True, servers
