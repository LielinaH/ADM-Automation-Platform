"""Named provider profile loading and resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adm_pipeline.providers import ProviderConfig
from adm_pipeline.utils import read_json


DEFAULT_PROFILES_PATH = Path("config/providers.json")


def load_profiles(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_PROFILES_PATH
    if not path.exists():
        return {"default_profile": None, "profiles": {}}
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Provider config at {path} must be an object")
    payload.setdefault("profiles", {})
    return payload


def resolve_profile(
    *,
    profile_name: str | None,
    config_path: Path | None,
    use_default_profile: bool = True,
    overrides: dict[str, Any] | None = None,
) -> ProviderConfig:
    payload = load_profiles(config_path)
    profiles = payload.get("profiles", {})
    selected_name = profile_name or (payload.get("default_profile") if use_default_profile else None)
    if selected_name:
        if selected_name not in profiles:
            raise RuntimeError(f"Unknown provider profile {selected_name!r}")
        merged = dict(profiles[selected_name])
        merged["profile_name"] = selected_name
    else:
        merged = {}
    for key, value in (overrides or {}).items():
        if value is not None:
            merged[key] = value
    if "provider_kind" not in merged or not merged["provider_kind"]:
        raise RuntimeError("provider_kind is required either in the selected profile or CLI overrides")
    return ProviderConfig(**merged)


def list_profiles(config_path: Path | None = None) -> tuple[str | None, dict[str, Any]]:
    payload = load_profiles(config_path)
    return payload.get("default_profile"), payload.get("profiles", {})
