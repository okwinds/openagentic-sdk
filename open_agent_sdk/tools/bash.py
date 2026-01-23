from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Mapping

from .base import Tool, ToolContext


@dataclass(frozen=True, slots=True)
class BashTool(Tool):
    name: str = "Bash"
    description: str = "Run a shell command."
    timeout_s: float = 60.0
    max_output_bytes: int = 1024 * 1024

    async def run(self, tool_input: Mapping[str, Any], ctx: ToolContext) -> dict[str, Any]:
        command = tool_input.get("command")
        if not isinstance(command, str) or not command:
            raise ValueError("Bash: 'command' must be a non-empty string")

        timeout_ms = tool_input.get("timeout")
        if timeout_ms is not None:
            timeout_s = float(timeout_ms) / 1000.0
        else:
            timeout_s = float(tool_input.get("timeout_s", self.timeout_s))
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd=ctx.cwd,
            capture_output=True,
            text=False,
            timeout=timeout_s,
        )
        stdout = proc.stdout or b""
        stderr = proc.stderr or b""
        stdout_truncated = len(stdout) > self.max_output_bytes
        stderr_truncated = len(stderr) > self.max_output_bytes
        if len(stdout) > self.max_output_bytes:
            stdout = stdout[: self.max_output_bytes]
        if len(stderr) > self.max_output_bytes:
            stderr = stderr[: self.max_output_bytes]
        output = (stdout + stderr).decode("utf-8", errors="replace")
        return {
            "command": command,
            "exit_code": int(proc.returncode),
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            # CAS-compatible aliases:
            "output": output,
            "exitCode": int(proc.returncode),
            "killed": False,
            "shellId": None,
        }
