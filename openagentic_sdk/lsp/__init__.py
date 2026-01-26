"""Language Server Protocol (LSP) integration.

This module provides a minimal stdio JSON-RPC client and a small manager that
selects/configures servers based on OpenCode-style `lsp` config.
"""

from .config import LspConfig, LspServerConfig, parse_lsp_config
from .manager import LspManager

__all__ = [
    "LspConfig",
    "LspServerConfig",
    "LspManager",
    "parse_lsp_config",
]
