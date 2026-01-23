from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .hooks.engine import HookEngine
from .permissions.gate import PermissionGate
from .providers.base import Provider
from .sessions.store import FileSessionStore
from .tools.registry import ToolRegistry
from .tools.defaults import default_tool_registry


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    description: str
    prompt: str
    tools: Sequence[str] = ()
    provider: Optional[Provider] = None
    model: Optional[str] = None


@dataclass(frozen=True, slots=True)
class OpenAgenticOptions:
    provider: Provider
    model: str
    api_key: str | None = None

    cwd: str = field(default_factory=os.getcwd)
    max_steps: int = 50
    timeout_s: float | None = None
    include_partial_messages: bool = False
    abort_event: Any | None = None

    tools: ToolRegistry = field(default_factory=default_tool_registry)
    allowed_tools: Sequence[str] | None = None

    permission_gate: PermissionGate = field(default_factory=lambda: PermissionGate(permission_mode="deny"))
    hooks: HookEngine = field(default_factory=HookEngine)

    session_store: FileSessionStore | None = None
    session_root: Path | None = None
    resume: str | None = None
    resume_max_events: int = 1000
    resume_max_bytes: int = 2_000_000

    setting_sources: Sequence[str] = ()
    project_dir: str | None = None

    agents: Mapping[str, AgentDefinition] = field(default_factory=dict)

    # MCP placeholders (not implemented yet)
    mcp_servers: Mapping[str, Any] | None = None
    mcp_registry: Any | None = None
