from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from .openai_responses import OpenAIResponsesProvider
from ..auth import ApiAuth, OAuthAuth, all_auth
from .models_dev import get_models_dev


@dataclass(frozen=True, slots=True)
class ModelRef:
    """OpenCode-style model reference.

    OpenCode config uses `provider/model`. Model IDs may contain `/`, so we only
    split on the first slash.
    """

    provider_id: str | None
    model_id: str
    raw: str


def parse_model_ref(value: str | None) -> ModelRef:
    s = str(value or "").strip()
    if not s:
        return ModelRef(provider_id=None, model_id="", raw="")
    if "/" in s:
        left, right = s.split("/", 1)
        left = left.strip()
        right = right.strip()
        if left and right:
            return ModelRef(provider_id=left, model_id=right, raw=s)
    return ModelRef(provider_id=None, model_id=s, raw=s)


@dataclass(frozen=True, slots=True)
class ResolvedSelection:
    provider: Any
    api_key: str | None
    model: str
    provider_id: str | None


def _string(v: Any) -> str | None:
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def resolve_provider_and_model(
    *,
    cfg: Mapping[str, Any] | None,
    model_ref: ModelRef,
    base_provider: Any,
    base_api_key: str | None,
) -> ResolvedSelection:
    """Resolve provider+model from config/auth.

    This keeps the runtime simple: it still receives a concrete provider object
    and a model string (without the provider prefix).
    """

    # Back-compat: no provider prefix => keep the base provider.
    if not model_ref.provider_id:
        return ResolvedSelection(
            provider=base_provider,
            api_key=base_api_key,
            model=model_ref.model_id,
            provider_id=getattr(base_provider, "name", None),
        )

    provider_id = model_ref.provider_id

    prov_cfg = cfg.get("provider") if isinstance(cfg, Mapping) else None
    spec = prov_cfg.get(provider_id) if isinstance(prov_cfg, Mapping) else None
    opts = spec.get("options") if isinstance(spec, Mapping) else None

    base_url = None
    timeout_ms = None
    api_key = None
    env_names: list[str] = []

    if isinstance(opts, Mapping):
        base_url = _string(opts.get("baseURL") or opts.get("baseUrl") or opts.get("base_url") or opts.get("url"))
        api_key = _string(opts.get("apiKey") or opts.get("api_key"))
        if isinstance(opts.get("timeout"), int):
            timeout_ms = int(opts.get("timeout"))

    if isinstance(spec, Mapping) and isinstance(spec.get("env"), list):
        env_names = [str(x) for x in spec.get("env") if isinstance(x, str) and x]

    # Models.dev provider metadata fallback (OpenCode parity): provides default
    # API base URL and env var names even when provider is not configured.
    if base_url is None or not env_names:
        try:
            db = get_models_dev()
            p = db.get(provider_id) if isinstance(db, dict) else None
            if isinstance(p, Mapping):
                if base_url is None:
                    base_url = _string(p.get("api"))
                if not env_names and isinstance(p.get("env"), list):
                    env_names = [str(x) for x in p.get("env") if isinstance(x, str) and x]
        except Exception:  # noqa: BLE001
            pass

    # Auth store fallback (OpenCode parity).
    if api_key is None:
        entry = all_auth().get(provider_id)
        if isinstance(entry, ApiAuth) and entry.key:
            api_key = entry.key
        elif isinstance(entry, OAuthAuth) and entry.access:
            # For providers that use OAuth bearer tokens, `access` is the token.
            api_key = entry.access

    # Env fallback using the provider's env[] list (when provided via config).
    if api_key is None and env_names:
        for nm in env_names:
            val = _string(os.environ.get(nm))
            if val:
                api_key = val
                break

    # Legacy fallback.
    if api_key is None:
        api_key = base_api_key

    # Provider object: we currently model everything as OpenAI-compatible
    # Responses API providers.
    provider_obj: Any
    if base_url:
        timeout_s = 120.0
        if isinstance(timeout_ms, int) and timeout_ms > 0:
            timeout_s = float(timeout_ms) / 1000.0
        provider_obj = OpenAIResponsesProvider(name=provider_id, base_url=base_url, timeout_s=timeout_s)
    else:
        provider_obj = OpenAIResponsesProvider(name=provider_id)

    return ResolvedSelection(provider=provider_obj, api_key=api_key, model=model_ref.model_id, provider_id=provider_id)
