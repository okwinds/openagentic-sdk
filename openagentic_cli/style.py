from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal

ANSI_RESET = "\x1b[0m"
ANSI_FG_DEFAULT = "\x1b[39m"
ANSI_FG_GREEN = "\x1b[32m"
ANSI_FG_BLUE = "\x1b[34m"
ANSI_BG_GRAY = "\x1b[100m"


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


def _wrap(text: str, seq: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{seq}{text}{ANSI_RESET}"


def bold(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[1m", enabled=enabled)


def dim(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[2m", enabled=enabled)


def fg_green(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[32m", enabled=enabled)


def fg_red(text: str, *, enabled: bool) -> str:
    return _wrap(text, "\x1b[31m", enabled=enabled)


class InlineCodeHighlighter:
    def __init__(self, *, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._in_fence = False
        self._in_inline = False
        self._pending_ticks = 0

    def feed(self, text: str) -> str:
        if not self.enabled or not text:
            return text

        out: list[str] = []
        for ch in text:
            if ch == "`":
                self._pending_ticks += 1
                if self._pending_ticks == 3:
                    if self._in_inline:
                        out.append(ANSI_FG_DEFAULT)
                        self._in_inline = False
                    out.append("```")
                    self._pending_ticks = 0
                    self._in_fence = not self._in_fence
                continue

            if self._pending_ticks:
                if self._pending_ticks == 1 and not self._in_fence:
                    if not self._in_inline:
                        out.append(ANSI_FG_BLUE + "`")
                        self._in_inline = True
                    else:
                        out.append("`" + ANSI_FG_DEFAULT)
                        self._in_inline = False
                else:
                    out.append("`" * self._pending_ticks)
                self._pending_ticks = 0

            out.append(ch)

        return "".join(out)


class StylizingStream:
    def __init__(self, raw, *, highlighter: InlineCodeHighlighter):  # noqa: ANN001
        self._raw = raw
        self._h = highlighter

    def write(self, s: str) -> int:
        out = self._h.feed(s)
        return self._raw.write(out)

    def flush(self) -> None:
        return self._raw.flush()

    def isatty(self) -> bool:  # pragma: no cover
        fn = getattr(self._raw, "isatty", None)
        return bool(fn()) if callable(fn) else False
