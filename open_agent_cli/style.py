from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class StyleConfig:
    color: Literal["auto", "always", "never"] = "auto"


def enable_windows_vt_mode() -> bool:
    if not sys.platform.startswith("win"):
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        if handle in (0, -1):
            return False

        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if kernel32.SetConsoleMode(handle, new_mode) == 0:
            return False
        return True
    except Exception:
        return False


def should_colorize(config: StyleConfig, *, isatty: bool, platform: str) -> bool:
    if os.getenv("NO_COLOR") is not None:
        return False
    if config.color == "always":
        if platform == "win32":
            enable_windows_vt_mode()
        return True
    if config.color == "never":
        return False
    if not isatty:
        return False
    if platform == "win32":
        return enable_windows_vt_mode()
    return True


_RESET = "\x1b[0m"


def _wrap(text: str, seq: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{seq}{text}{_RESET}"


def bold(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[1m", enabled=enabled)


def dim(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[2m", enabled=enabled)


def fg_green(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[32m", enabled=enabled)


def fg_red(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[31m", enabled=enabled)

