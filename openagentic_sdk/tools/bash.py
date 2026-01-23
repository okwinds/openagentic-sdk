from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class BashTool(Tool):
    name: str = "Bash"
    description: str = "Run a shell command."
    timeout_s: float = 60.0
    max_output_bytes: int = 1024 * 1024
    max_output_lines: int = 2000

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        command = tool_input.get("command")
        if not isinstance(command, str) or not command:
            raise ValueError("Bash: 'command' must be a non-empty string")

        workdir = tool_input.get("workdir")
        if workdir is not None and not isinstance(workdir, str):
            raise ValueError("Bash: 'workdir' must be a string")
        run_cwd = Path(ctx.cwd) if not workdir else Path(workdir)
        if not run_cwd.is_absolute():
            run_cwd = Path(ctx.cwd) / run_cwd

        timeout_ms = tool_input.get("timeout")
        if timeout_ms is not None:
            timeout_s = float(timeout_ms) / 1000.0
        else:
            timeout_s = float(tool_input.get("timeout_s", self.timeout_s))
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(run_cwd),
            capture_output=True,
            text=False,
            timeout=timeout_s,
        )
        stdout_full = proc.stdout or b""
        stderr_full = proc.stderr or b""
        stdout_truncated = len(stdout_full) > self.max_output_bytes
        stderr_truncated = len(stderr_full) > self.max_output_bytes
        stdout = stdout_full[: self.max_output_bytes]
        stderr = stderr_full[: self.max_output_bytes]

        output = (stdout + stderr).decode("utf-8", errors="replace")
        lines = output.splitlines()
        output_lines_truncated = len(lines) > self.max_output_lines
        if output_lines_truncated:
            output = "\n".join(lines[: self.max_output_lines])

        full_output_file_path: str | None = None
        if (stdout_truncated or stderr_truncated or output_lines_truncated) and ctx.project_dir:
            try:
                out_dir = Path(ctx.project_dir) / ".open-agent-sdk" / "tool-output"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"bash.{uuid.uuid4().hex}.txt"
                out_path.write_bytes(stdout_full + stderr_full)
                full_output_file_path = str(out_path)
            except Exception:  # pragma: no cover
                full_output_file_path = None

        return {
            "command": command,
            "exit_code": int(proc.returncode),
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "output_lines_truncated": output_lines_truncated,
            "full_output_file_path": full_output_file_path,
            # CAS-compatible aliases:
            "output": output,
            "exitCode": int(proc.returncode),
            "killed": False,
            "shellId": None,
        }
