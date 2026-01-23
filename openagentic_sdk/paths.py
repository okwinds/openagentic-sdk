from __future__ import annotations

import os
from pathlib import Path

NEW_HOME_ENV = "OPENAGENTIC_SDK_HOME"

NEW_DEFAULT_DIRNAME = ".openagentic-sdk"


def default_session_root() -> Path:
    env = os.environ.get(NEW_HOME_ENV)
    if env:
        return Path(env).expanduser()

    home = Path.home()
    return home / NEW_DEFAULT_DIRNAME
