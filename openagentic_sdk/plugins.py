from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence

from .hooks.engine import HookEngine
from .hooks.models import HookMatcher
from .tools.base import Tool


@dataclass(frozen=True, slots=True)
class LoadedPlugins:
    tools: list[Tool]
    hooks: HookEngine


def _merge_hooks(a: HookEngine, b: HookEngine) -> HookEngine:
    return HookEngine(
        pre_tool_use=[*a.pre_tool_use, *b.pre_tool_use],
        post_tool_use=[*a.post_tool_use, *b.post_tool_use],
        user_prompt_submit=[*a.user_prompt_submit, *b.user_prompt_submit],
        before_model_call=[*a.before_model_call, *b.before_model_call],
        after_model_call=[*a.after_model_call, *b.after_model_call],
        session_start=[*a.session_start, *b.session_start],
        session_end=[*a.session_end, *b.session_end],
        session_compacting=[*a.session_compacting, *b.session_compacting],
        stop=[*a.stop, *b.stop],
        enable_message_rewrite_hooks=(a.enable_message_rewrite_hooks or b.enable_message_rewrite_hooks),
    )


def merge_hook_engines(*engines: HookEngine) -> HookEngine:
    out = HookEngine()
    for e in engines:
        out = _merge_hooks(out, e)
    return out


class PluginRegistry:
    def __init__(self) -> None:
        self.tools: list[Tool] = []
        self.hooks = HookEngine()

    def add_tool(self, tool: Tool) -> None:
        self.tools.append(tool)

    def add_hooks(self, hooks: HookEngine) -> None:
        self.hooks = _merge_hooks(self.hooks, hooks)

    def add_before_model_call(self, matcher: HookMatcher) -> None:
        self.hooks = _merge_hooks(self.hooks, HookEngine(before_model_call=[matcher]))

    def add_pre_tool_use(self, matcher: HookMatcher) -> None:
        self.hooks = _merge_hooks(self.hooks, HookEngine(pre_tool_use=[matcher]))

    def add_post_tool_use(self, matcher: HookMatcher) -> None:
        self.hooks = _merge_hooks(self.hooks, HookEngine(post_tool_use=[matcher]))


def _load_module_from_file(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load plugin module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[call-arg]
    return mod


def _load_plugin_module(spec: str, *, project_dir: str | None = None) -> ModuleType:
    s = str(spec or "").strip()
    if not s:
        raise ValueError("empty plugin spec")
    if s.startswith("file://"):
        s = s[len("file://") :]

    p = Path(s)
    if not p.is_absolute() and project_dir:
        p = Path(project_dir) / p
    if p.exists() and p.is_file():
        return _load_module_from_file(p)

    return importlib.import_module(s)


def load_plugins(specs: Sequence[str] | None, *, project_dir: str | None = None) -> LoadedPlugins:
    reg = PluginRegistry()
    hooks = HookEngine()
    tools: list[Tool] = []

    for raw in list(specs or []):
        if not isinstance(raw, str) or not raw.strip():
            continue
        mod = _load_plugin_module(raw, project_dir=project_dir)

        # Convention 1: register(registry)
        register = getattr(mod, "register", None)
        if callable(register):
            register(reg)
        else:
            # Convention 2: PLUGIN dict-like
            plugin_obj = getattr(mod, "PLUGIN", None)
            if isinstance(plugin_obj, dict):
                if isinstance(plugin_obj.get("hooks"), HookEngine):
                    reg.add_hooks(plugin_obj["hooks"])
                if isinstance(plugin_obj.get("tools"), list):
                    for t in plugin_obj.get("tools") or []:
                        if isinstance(t, Tool):
                            reg.add_tool(t)

    hooks = _merge_hooks(hooks, reg.hooks)
    tools.extend(reg.tools)
    return LoadedPlugins(tools=tools, hooks=hooks)


def plugins_from_opencode_config(cfg: Any) -> list[str]:
    if not isinstance(cfg, dict):
        return []
    plugins = cfg.get("plugin") or cfg.get("plugins")
    if not isinstance(plugins, list):
        return []
    out: list[str] = []
    for p in plugins:
        if isinstance(p, str) and p.strip():
            out.append(p.strip())
    return out
