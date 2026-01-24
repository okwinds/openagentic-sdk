from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ModelVariant:
    name: str
    disabled: bool = False
    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    variants: tuple[ModelVariant, ...] = ()
    raw: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    name: str
    options: Mapping[str, Any] | None = None
    models: tuple[ModelInfo, ...] = ()
    raw: Mapping[str, Any] | None = None


def providers_from_opencode_config(cfg: Mapping[str, Any] | None) -> dict[str, ProviderInfo]:
    if not isinstance(cfg, Mapping):
        return {}
    raw = cfg.get("provider")
    if not isinstance(raw, Mapping):
        return {}

    out: dict[str, ProviderInfo] = {}
    for name, spec in raw.items():
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(spec, Mapping):
            continue
        options = spec.get("options")
        options2 = dict(options) if isinstance(options, Mapping) else None

        models: list[ModelInfo] = []
        models_raw = spec.get("models")
        if isinstance(models_raw, Mapping):
            for model_name, model_spec in models_raw.items():
                if not isinstance(model_name, str) or not model_name:
                    continue
                if not isinstance(model_spec, Mapping):
                    continue
                variants: list[ModelVariant] = []
                variants_raw = model_spec.get("variants")
                if isinstance(variants_raw, Mapping):
                    for vname, vspec in variants_raw.items():
                        if not isinstance(vname, str) or not vname:
                            continue
                        if not isinstance(vspec, Mapping):
                            continue
                        disabled = bool(vspec.get("disabled", False))
                        variants.append(ModelVariant(name=vname, disabled=disabled, raw=dict(vspec)))
                models.append(ModelInfo(name=model_name, variants=tuple(variants), raw=dict(model_spec)))

        out[name] = ProviderInfo(name=name, options=options2, models=tuple(models), raw=dict(spec))
    return out


def list_configured_models(cfg: Mapping[str, Any] | None) -> list[str]:
    provs = providers_from_opencode_config(cfg)
    names: set[str] = set()
    for p in provs.values():
        for m in p.models:
            names.add(m.name)
    return sorted(names)


def list_model_variants(cfg: Mapping[str, Any] | None, *, model: str) -> list[str]:
    provs = providers_from_opencode_config(cfg)
    out: set[str] = set()
    for p in provs.values():
        for m in p.models:
            if m.name != model:
                continue
            for v in m.variants:
                if not v.disabled:
                    out.add(v.name)
    return sorted(out)
