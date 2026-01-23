from __future__ import annotations

import importlib
import warnings
from typing import Any

warnings.warn(
    "`open_agent_sdk` has been renamed to `openagentic_sdk`; please update imports.",
    DeprecationWarning,
    stacklevel=2,
)

_new = importlib.import_module("openagentic_sdk")

__all__ = getattr(_new, "__all__", ())

# Make `open_agent_sdk.<submodule>` importable from the new package location.
__path__ = _new.__path__  # type: ignore[attr-defined]


def __getattr__(name: str) -> Any:  # noqa: ANN401
    return getattr(_new, name)


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(dir(_new)))
