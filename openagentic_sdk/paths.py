from __future__ import annotations

import os
from pathlib import Path

HOME_ENV = "OPENAGENTIC_HOME"
LEGACY_HOME_ENV = "OPENAGENTIC_SDK_HOME"

DEFAULT_DIRNAME = ".openagentic"
LEGACY_DIRNAME = ".openagentic-sdk"


def default_session_root() -> Path:
    env = os.environ.get(HOME_ENV) or os.environ.get(LEGACY_HOME_ENV)
    if env:
        return Path(env).expanduser()

    home = Path.home()
    new_path = home / DEFAULT_DIRNAME
    legacy_path = home / LEGACY_DIRNAME
    if new_path.exists():
        return new_path
    if legacy_path.exists():
        return legacy_path
    return new_path
