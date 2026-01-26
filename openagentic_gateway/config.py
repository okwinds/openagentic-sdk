from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Placeholder config for the Gateway control plane (v1).

    The initial milestone only needs a running server; configuration will be
    expanded in later tasks.
    """

    pass

