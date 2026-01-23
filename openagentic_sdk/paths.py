from __future__ import annotations

import os
from pathlib import Path

NEW_HOME_ENV = "OPENAGENTIC_SDK_HOME"
LEGACY_HOME_ENV = "OPEN_AGENT_SDK_HOME"

NEW_DEFAULT_DIRNAME = ".openagentic-sdk"
LEGACY_DEFAULT_DIRNAME = ".open-agent-sdk"


def default_session_root() -> Path:
    env = os.environ.get(NEW_HOME_ENV)
    if env:
        return Path(env).expanduser()

    env = os.environ.get(LEGACY_HOME_ENV)
    if env:
        return Path(env).expanduser()

    home = Path.home()
    new_root = home / NEW_DEFAULT_DIRNAME
    legacy_root = home / LEGACY_DEFAULT_DIRNAME

    if new_root.exists():
        return new_root
    if legacy_root.exists():
        return legacy_root
    return new_root

