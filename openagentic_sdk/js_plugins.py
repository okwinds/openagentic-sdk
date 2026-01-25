from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .tools.base import Tool, ToolContext


def _runner_path() -> Path:
    return Path(__file__).resolve().parent / "js_runner" / "opencode_tool_runner.mjs"


def _bun_path() -> str | None:
    return shutil.which("bun")


def _parse_json_from_stdout(stdout: str) -> Any:
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("no JSON output")
    return json.loads(lines[-1])


def _bun_call(argv: Sequence[str], *, timeout_s: float) -> Any:
    bun = _bun_path()
    if bun is None:
        raise RuntimeError("bun is required to run JS/TS plugins")

    res = subprocess.run(
        [bun, str(_runner_path()), *argv],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        stdout = (res.stdout or "").strip()
        raise RuntimeError(f"bun plugin runner failed:\nstdout={stdout}\nstderr={stderr}")
    return _parse_json_from_stdout(res.stdout)


def _openai_schema(name: str, description: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
    params: dict[str, Any]
    if isinstance(parameters, dict) and parameters.get("type") == "object":
        params = dict(parameters)
    else:
        params = {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": params,
        },
    }


def _resolve_file_spec(spec: str, *, project_dir: str) -> Path | None:
    s = str(spec or "").strip()
    if not s:
        return None
    if s.startswith("file://"):
        s = s[len("file://") :]
    p = Path(s)
    if not p.is_absolute():
        p = Path(project_dir) / p
    p = p.resolve()
    if not p.exists() or not p.is_file():
        return None
    if p.suffix not in {".js", ".ts"}:
        return None
    return p


def split_plugin_specs(specs: Sequence[str], *, project_dir: str) -> tuple[list[str], list[str]]:
    """Split plugin specs into (python_specs, js_specs).

    This prevents the Python plugin loader from attempting to import JS/TS files.
    """

    py: list[str] = []
    js: list[str] = []
    for raw in list(specs or []):
        if not isinstance(raw, str) or not raw.strip():
            continue
        p = _resolve_file_spec(raw, project_dir=project_dir)
        if p is not None:
            js.append(raw)
        else:
            py.append(raw)
    return py, js


@dataclass(frozen=True, slots=True)
class JsPluginToolWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _plugin_file: str
    _plugin_export: str
    _tool_id: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        payload_ctx: dict[str, Any] = {"cwd": ctx.cwd}
        if ctx.project_dir:
            payload_ctx["project_dir"] = ctx.project_dir
        obj = _bun_call(
            [
                "--mode",
                "plugin_execute",
                "--file",
                self._plugin_file,
                "--export",
                self._plugin_export,
                "--tool-id",
                self._tool_id,
                "--args",
                json.dumps(dict(tool_input), ensure_ascii=False),
                "--ctx",
                json.dumps(payload_ctx, ensure_ascii=False),
            ],
            timeout_s=120.0,
        )
        return {"output": obj.get("result") if isinstance(obj, dict) else obj}


def load_js_plugin_tools(*, plugin_specs: Sequence[str], project_dir: str, enabled: bool) -> list[Tool]:
    if not enabled:
        return []
    if _bun_path() is None:
        return []

    out: list[Tool] = []
    for spec in list(plugin_specs or []):
        p = _resolve_file_spec(spec, project_dir=project_dir)
        if p is None:
            continue
        try:
            desc_obj = _bun_call(
                [
                    "--mode",
                    "plugin_describe",
                    "--file",
                    str(p),
                    "--ctx",
                    json.dumps({"cwd": project_dir}, ensure_ascii=False),
                ],
                timeout_s=30.0,
            )
        except Exception:
            continue

        tools = desc_obj.get("tools") if isinstance(desc_obj, dict) else None
        if not isinstance(tools, list):
            continue

        for t in tools:
            if not isinstance(t, dict):
                continue
            tool_id = t.get("toolId")
            export_name = t.get("export")
            if not isinstance(tool_id, str) or not tool_id:
                continue
            if not isinstance(export_name, str) or not export_name:
                continue

            desc = t.get("description") if isinstance(t.get("description"), str) else ""
            params_raw = t.get("parameters")
            params: dict[str, Any] = {"type": "object", "properties": {}}
            if isinstance(params_raw, dict):
                params = {str(k): v for k, v in params_raw.items()}

            desc2 = (desc or f"JS plugin tool {tool_id}").strip()
            desc2 = f"{desc2}\n\nOrigin: {p} ({export_name})"
            out.append(
                JsPluginToolWrapper(
                    name=tool_id,
                    description=desc2,
                    openai_schema=_openai_schema(tool_id, desc2, params),
                    _plugin_file=str(p),
                    _plugin_export=export_name,
                    _tool_id=tool_id,
                )
            )
    return out
