from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .tools.base import Tool, ToolContext


def _default_global_opencode_config_dir() -> Path:
    return Path(os.environ.get("OPENCODE_CONFIG_DIR") or (Path.home() / ".config" / "opencode")).expanduser()


def discover_js_tool_files(*, project_dir: str) -> list[Path]:
    """Discover OpenCode-style JS/TS tools under {tool,tools} directories.

    Matches OpenCode's `new Bun.Glob("{tool,tools}/*.{js,ts}")` behavior, but limited to the
    same roots we already scan for Python custom tools:
    - <project>/.opencode/{tool,tools}
    - <project>/{tool,tools}
    - ${OPENCODE_CONFIG_DIR}/{tool,tools}
    """

    base = Path(project_dir)
    global_root = _default_global_opencode_config_dir()

    roots: list[Path] = [
        base / ".opencode",
        base,
        global_root,
    ]

    out: list[Path] = []
    for r in roots:
        for dirname in ("tool", "tools"):
            d = r / dirname
            if not d.exists() or not d.is_dir():
                continue
            for ext in ("*.js", "*.ts"):
                out.extend([p for p in sorted(d.glob(ext)) if p.is_file()])
    return sorted(out, key=lambda p: str(p))


def _runner_path() -> Path:
    return Path(__file__).resolve().parent / "js_runner" / "opencode_tool_runner.mjs"


def _bun_path() -> str | None:
    return shutil.which("bun")


def _parse_json_from_stdout(stdout: str) -> Any:
    # Tool modules might print; take the last non-empty line as the payload.
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    if not lines:
        raise ValueError("no JSON output")
    return json.loads(lines[-1])


def _bun_call(*, mode: str, file_path: Path, export_name: str | None, args: Mapping[str, Any] | None, ctx: Mapping[str, Any]) -> Any:
    bun = _bun_path()
    if bun is None:
        raise RuntimeError("bun is required to run JS/TS custom tools")

    runner = _runner_path()
    cmd: list[str] = [bun, str(runner), "--mode", mode, "--file", str(file_path)]
    if export_name is not None:
        cmd.extend(["--export", export_name])
    if args is not None:
        cmd.extend(["--args", json.dumps(dict(args), ensure_ascii=False)])
    cmd.extend(["--ctx", json.dumps(dict(ctx), ensure_ascii=False)])

    timeout_s = 30.0 if mode == "describe" else 120.0
    res = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    if res.returncode != 0:
        stderr = (res.stderr or "").strip()
        stdout = (res.stdout or "").strip()
        raise RuntimeError(f"bun tool runner failed (mode={mode}, file={file_path}):\nstdout={stdout}\nstderr={stderr}")
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


@dataclass(frozen=True, slots=True)
class JsToolWrapper(Tool):
    name: str
    description: str
    openai_schema: dict[str, Any]
    _file_path: str
    _export_name: str

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        payload_ctx: dict[str, Any] = {"cwd": ctx.cwd}
        if ctx.project_dir:
            payload_ctx["project_dir"] = ctx.project_dir
        obj = _bun_call(
            mode="execute",
            file_path=Path(self._file_path),
            export_name=self._export_name,
            args=tool_input,
            ctx=payload_ctx,
        )
        # Stable surface: expose tool result under a single key.
        return {"output": obj.get("result") if isinstance(obj, dict) else obj}


def load_js_tools(*, project_dir: str, enabled: bool) -> list[Tool]:
    if not enabled:
        return []
    if _bun_path() is None:
        return []

    out: list[Tool] = []
    for p in discover_js_tool_files(project_dir=project_dir):
        namespace = p.stem
        try:
            desc_obj = _bun_call(mode="describe", file_path=p, export_name=None, args=None, ctx={"cwd": project_dir})
        except Exception:
            # Do not crash the CLI on a single broken tool; match OpenCode's resilience.
            continue

        exports = desc_obj.get("exports") if isinstance(desc_obj, dict) else None
        if not isinstance(exports, list):
            continue

        # Stable ordering: sort by export key.
        exports2 = [e for e in exports if isinstance(e, dict) and isinstance(e.get("export"), str)]
        exports2.sort(key=lambda e: str(e.get("export")))

        for e in exports2:
            export_name = str(e.get("export"))
            tool_id = namespace if export_name == "default" else f"{namespace}_{export_name}"
            desc = e.get("description") if isinstance(e.get("description"), str) else ""
            params = e.get("parameters") if isinstance(e.get("parameters"), dict) else {"type": "object", "properties": {}}

            # Provenance: include origin in the model-visible description.
            desc2 = (desc or f"Custom JS tool {tool_id}").strip()
            desc2 = f"{desc2}\n\nOrigin: {p}"

            out.append(
                JsToolWrapper(
                    name=tool_id,
                    description=desc2,
                    openai_schema=_openai_schema(tool_id, desc2, params),
                    _file_path=str(p),
                    _export_name=export_name,
                )
            )
    return out
