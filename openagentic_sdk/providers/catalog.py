from __future__ import annotations

import os
from typing import Any, Mapping

from ..auth import ApiAuth, OAuthAuth, all_auth
from .models_dev import get_models_dev


def _env_flag(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    if v == "":
        return True
    return str(v).strip().lower() not in {"0", "false", "no", "off"}


def _str_list(v: Any) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if isinstance(x, str) and x]


def _str_dict(v: Any) -> dict[str, Any]:
    return dict(v) if isinstance(v, Mapping) else {}


def _provider_allowed(cfg: Mapping[str, Any], provider_id: str) -> bool:
    disabled = set(_str_list(cfg.get("disabled_providers")))
    enabled_raw = cfg.get("enabled_providers")
    enabled = set(_str_list(enabled_raw)) if isinstance(enabled_raw, list) else None
    if enabled is not None and provider_id not in enabled:
        return False
    if provider_id in disabled:
        return False
    return True


def _model_allowed(model: Mapping[str, Any]) -> bool:
    status = model.get("status")
    if status == "deprecated":
        return False
    if status == "alpha" and not _env_flag("OPENCODE_ENABLE_EXPERIMENTAL_MODELS"):
        return False
    return True


def _build_model(provider: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    provider_id = str(provider.get("id") or "")
    provider_api = provider.get("api") if isinstance(provider.get("api"), str) else ""
    provider_npm = provider.get("npm") if isinstance(provider.get("npm"), str) else None
    model_provider = model.get("provider") if isinstance(model.get("provider"), Mapping) else None
    model_npm = model_provider.get("npm") if isinstance(model_provider, Mapping) and isinstance(model_provider.get("npm"), str) else None

    limit = model.get("limit") if isinstance(model.get("limit"), Mapping) else {}
    cost = model.get("cost") if isinstance(model.get("cost"), Mapping) else None
    modalities = model.get("modalities") if isinstance(model.get("modalities"), Mapping) else None
    input_modalities = []
    output_modalities = []
    if isinstance(modalities, Mapping):
        im = modalities.get("input")
        om = modalities.get("output")
        if isinstance(im, list):
            input_modalities = [str(x) for x in im if isinstance(x, str)]
        if isinstance(om, list):
            output_modalities = [str(x) for x in om if isinstance(x, str)]
    interleaved = model.get("interleaved")

    return {
        "id": str(model.get("id") or ""),
        "providerID": provider_id,
        "name": str(model.get("name") or ""),
        "family": model.get("family") if isinstance(model.get("family"), str) else "",
        "api": {
            "id": str(model.get("id") or ""),
            "url": provider_api,
            "npm": model_npm or provider_npm or "@ai-sdk/openai-compatible",
        },
        "status": str(model.get("status") or "active"),
        "headers": _str_dict(model.get("headers")),
        "options": _str_dict(model.get("options")),
        "cost": {
            "input": float(cost.get("input")) if isinstance(cost, Mapping) and isinstance(cost.get("input"), (int, float)) else 0.0,
            "output": float(cost.get("output")) if isinstance(cost, Mapping) and isinstance(cost.get("output"), (int, float)) else 0.0,
            "cache": {
                "read": float(cost.get("cache_read")) if isinstance(cost, Mapping) and isinstance(cost.get("cache_read"), (int, float)) else 0.0,
                "write": float(cost.get("cache_write")) if isinstance(cost, Mapping) and isinstance(cost.get("cache_write"), (int, float)) else 0.0,
            },
        },
        "limit": {
            "context": int(limit.get("context") or 0),
            "input": int(limit.get("input") or 0) or None,
            "output": int(limit.get("output") or 0),
        },
        "capabilities": {
            "temperature": bool(model.get("temperature")),
            "reasoning": bool(model.get("reasoning")),
            "attachment": bool(model.get("attachment")),
            "toolcall": bool(model.get("tool_call")),
            "input": {
                "text": "text" in input_modalities,
                "audio": "audio" in input_modalities,
                "image": "image" in input_modalities,
                "video": "video" in input_modalities,
                "pdf": "pdf" in input_modalities,
            },
            "output": {
                "text": "text" in output_modalities,
                "audio": "audio" in output_modalities,
                "image": "image" in output_modalities,
                "video": "video" in output_modalities,
                "pdf": "pdf" in output_modalities,
            },
            "interleaved": interleaved,
        },
        "release_date": model.get("release_date") if isinstance(model.get("release_date"), str) else "",
        "variants": _str_dict(model.get("variants")),
    }


def build_provider_listing(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    cfg2: Mapping[str, Any] = cfg if isinstance(cfg, Mapping) else {}
    db = get_models_dev()
    auth = all_auth()
    prov_cfg = cfg2.get("provider") if isinstance(cfg2.get("provider"), Mapping) else {}

    providers_out: list[dict[str, Any]] = []
    connected: list[str] = []
    default: dict[str, str] = {}

    # Union of models.dev providers and config providers.
    provider_ids: set[str] = set()
    for k in db.keys():
        if isinstance(k, str) and k:
            provider_ids.add(k)
    for k in prov_cfg.keys():
        if isinstance(k, str) and k:
            provider_ids.add(k)

    for pid in sorted(provider_ids):
        if not _provider_allowed(cfg2, pid):
            continue

        base = db.get(pid) if isinstance(db.get(pid), Mapping) else {}
        spec = prov_cfg.get(pid) if isinstance(prov_cfg, Mapping) else None
        spec_models = spec.get("models") if isinstance(spec, Mapping) and isinstance(spec.get("models"), Mapping) else {}
        whitelist = set(_str_list(spec.get("whitelist"))) if isinstance(spec, Mapping) else set()
        blacklist = set(_str_list(spec.get("blacklist"))) if isinstance(spec, Mapping) else set()

        name = pid
        env_list = _str_list(base.get("env"))
        source = "custom" if base else "config"

        if isinstance(base.get("name"), str) and base.get("name"):
            name = str(base.get("name"))
        if isinstance(spec, Mapping):
            if isinstance(spec.get("name"), str) and spec.get("name"):
                name = str(spec.get("name"))
            if isinstance(spec.get("env"), list):
                env_list = _str_list(spec.get("env"))

        # Determine connectedness (credentials available).
        has_key = False
        if isinstance(spec, Mapping):
            opts = spec.get("options") if isinstance(spec.get("options"), Mapping) else None
            if isinstance(opts, Mapping):
                ak = opts.get("apiKey")
                if isinstance(ak, str) and ak.strip():
                    has_key = True
                    source = "config"

        if not has_key:
            a = auth.get(pid)
            if isinstance(a, ApiAuth) and a.key:
                has_key = True
                source = "api"
            elif isinstance(a, OAuthAuth) and a.access:
                has_key = True
                source = "oauth"

        if not has_key and env_list:
            for nm in env_list:
                v = os.environ.get(nm)
                if isinstance(v, str) and v.strip():
                    has_key = True
                    source = "env"
                    break

        if has_key:
            connected.append(pid)

        # Models from models.dev (filtered).
        models_raw = base.get("models") if isinstance(base.get("models"), Mapping) else {}
        models_out: dict[str, Any] = {}
        for mid, m in models_raw.items():
            if not isinstance(mid, str) or not mid:
                continue
            if whitelist and mid not in whitelist:
                continue
            if blacklist and mid in blacklist:
                continue
            if not isinstance(m, Mapping):
                continue
            if not _model_allowed(m):
                continue

            built = _build_model(base, m)

            # Apply config variant overrides (disable/merge) when present.
            model_spec = spec_models.get(mid) if isinstance(spec_models, Mapping) else None
            variants_spec = model_spec.get("variants") if isinstance(model_spec, Mapping) and isinstance(model_spec.get("variants"), Mapping) else None
            if variants_spec is not None and isinstance(built.get("variants"), dict):
                variants_out = dict(built.get("variants") or {})
                for vname, vspec in variants_spec.items():
                    if not isinstance(vname, str) or not vname:
                        continue
                    if isinstance(vspec, Mapping) and bool(vspec.get("disabled")):
                        variants_out.pop(vname, None)
                        continue
                    if isinstance(vspec, Mapping):
                        cur = variants_out.get(vname)
                        cur2 = dict(cur) if isinstance(cur, Mapping) else {}
                        cur2.update({str(k): v for k, v in vspec.items() if k != "disabled"})
                        variants_out[vname] = cur2
                built["variants"] = variants_out

            models_out[mid] = built

        # Default model selection (deterministic, alphabetical).
        if models_out:
            default[pid] = sorted(models_out.keys())[0]

        providers_out.append(
            {
                "id": pid,
                "name": name,
                "source": source,
                "env": env_list,
                "options": {},
                "models": models_out,
            }
        )

    return {"all": providers_out, "default": default, "connected": connected}
