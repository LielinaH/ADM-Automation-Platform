"""Section generation, prompt building, persistence, and provider selection."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import time

from adm_pipeline.constants import BENCHMARK_STYLE_VERSION, PROMPT_SET_VERSION, SECTION_CONFIG_BY_ID, SECTION_SCHEMA_VERSION
from adm_pipeline.providers import LMStudioProvider, MockProvider, OpenAIResponsesProvider, OpenRouterProvider, ProviderConfig, SectionProvider
from adm_pipeline.run_state import load_manifest, save_manifest
from adm_pipeline.sections import section_json_schema, validate_section_payload
from adm_pipeline.types import JsonObject
from adm_pipeline.utils import read_json, write_json


def resolve_provider(config: ProviderConfig) -> SectionProvider:
    providers = {
        "mock": MockProvider,
        "openai_responses": OpenAIResponsesProvider,
        "lmstudio_openai_compat": LMStudioProvider,
        "openrouter": OpenRouterProvider,
    }
    if config.provider_kind not in providers:
        raise RuntimeError(f"Unsupported provider {config.provider_kind}")
    return providers[config.provider_kind](config)


def build_prompt(section_packet: JsonObject, schema: JsonObject) -> str:
    section_id = section_packet["section_id"]
    config = SECTION_CONFIG_BY_ID[section_id]
    return (
        f"You are generating section {section_id} ({config.title}) for an ADM document.\n"
        f"Prompt set version: {PROMPT_SET_VERSION}\n"
        f"Benchmark style version: {BENCHMARK_STYLE_VERSION}\n"
        f"Section schema version: {SECTION_SCHEMA_VERSION}\n"
        "Return JSON only, matching the supplied schema.\n"
        "Do not emit HTML. All figures must come from the provided facts and section input packet.\n"
        "Keep the tone analytical, benchmark-oriented, and executive-ready.\n\n"
        f"Schema:\n{json.dumps(schema, indent=2)}\n\n"
        f"Section input packet:\n{json.dumps(section_packet, indent=2)}"
    )


def generate_sections(
    run_dir: Path,
    section_inputs: dict[str, JsonObject],
    provider_config: ProviderConfig,
    *,
    force: bool = False,
) -> dict[str, JsonObject]:
    provider = resolve_provider(provider_config)
    manifest = load_manifest(run_dir)
    generated: dict[str, JsonObject] = {}
    for section_id, packet in section_inputs.items():
        normalized_path = run_dir / "sections" / f"{section_id}.normalized.json"
        if normalized_path.exists() and not force:
            existing = read_json(normalized_path)
            if validate_section_payload(section_id, existing).ok:
                generated[section_id] = existing
                manifest.setdefault("sections", {}).setdefault(section_id, {})
                manifest["sections"][section_id].update(
                    {
                        "title": SECTION_CONFIG_BY_ID[section_id].title,
                        "status": "cached",
                    }
                )
                continue
                continue
        generated[section_id] = _generate_one_section(
            run_dir,
            manifest,
            provider,
            provider_config,
            packet,
            repair_notes=None,
        )
        save_manifest(run_dir, manifest)
    _refresh_manifest_totals(manifest)
    save_manifest(run_dir, manifest)
    return generated


def repair_sections(
    run_dir: Path,
    section_inputs: dict[str, JsonObject],
    provider_config: ProviderConfig,
    repair_map: dict[str, list[str]],
) -> dict[str, JsonObject]:
    if not repair_map:
        return {}
    provider = resolve_provider(provider_config)
    manifest = load_manifest(run_dir)
    repaired: dict[str, JsonObject] = {}
    for section_id, notes in repair_map.items():
        repaired[section_id] = _generate_one_section(
            run_dir,
            manifest,
            provider,
            provider_config,
            section_inputs[section_id],
            repair_notes=notes,
        )
    _refresh_manifest_totals(manifest)
    save_manifest(run_dir, manifest)
    return repaired


def _generate_one_section(
    run_dir: Path,
    manifest: JsonObject,
    provider: SectionProvider,
    provider_config: ProviderConfig,
    packet: JsonObject,
    repair_notes: list[str] | None,
) -> JsonObject:
    section_id = packet["section_id"]
    raw_path = run_dir / "sections" / f"{section_id}.raw.json"
    normalized_path = run_dir / "sections" / f"{section_id}.normalized.json"
    request_path = run_dir / "sections" / f"{section_id}.request.json"
    schema = section_json_schema(section_id)
    prompt = build_prompt(packet, schema)
    write_json(
        request_path,
        {
            "section_id": section_id,
            "packet": packet,
            "schema": schema,
            "prompt": prompt,
            "repair_notes": repair_notes or [],
        },
    )
    attempt = 0
    last_error: str | None = None
    while attempt <= provider_config.max_retries:
        attempt += 1
        started = time.perf_counter()
        try:
            result = provider.generate_section(packet, schema, prompt, repair_notes=repair_notes)
            report = validate_section_payload(section_id, result.normalized)
            if not report.ok:
                raise RuntimeError("; ".join(report.errors))
            write_json(raw_path, result.raw_response)
            write_json(normalized_path, result.normalized)
            duration = round(time.perf_counter() - started, 3)
            manifest.setdefault("sections", {})[section_id] = {
                "title": SECTION_CONFIG_BY_ID[section_id].title,
                "duration_seconds": duration,
                "retry_count": attempt - 1,
                "provider": provider_config.provider_kind,
                "model": provider_config.model,
                "usage": asdict(result.usage),
                "response_id": result.response_id,
                "status": "repaired" if repair_notes else "generated",
                "repair_notes": repair_notes or [],
            }
            return result.normalized
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt > provider_config.max_retries:
                manifest.setdefault("sections", {})[section_id] = {
                    "title": SECTION_CONFIG_BY_ID[section_id].title,
                    "duration_seconds": None,
                    "retry_count": attempt - 1,
                    "provider": provider_config.provider_kind,
                    "model": provider_config.model,
                    "usage": {},
                    "response_id": None,
                    "status": "failed",
                    "repair_notes": repair_notes or [],
                    "error": last_error,
                }
                raise RuntimeError(f"Failed to generate {section_id}: {last_error}") from exc
    raise RuntimeError(f"Failed to generate {section_id}: {last_error}")


def _refresh_manifest_totals(manifest: JsonObject) -> None:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    estimated_cost = 0.0
    saw_input = False
    saw_output = False
    saw_total = False
    saw_cost = False
    total_duration = 0.0
    for section in manifest.get("sections", {}).values():
        usage = section.get("usage", {})
        if isinstance(usage.get("input_tokens"), int):
            input_tokens += usage["input_tokens"]
            saw_input = True
        if isinstance(usage.get("output_tokens"), int):
            output_tokens += usage["output_tokens"]
            saw_output = True
        if isinstance(usage.get("total_tokens"), int):
            total_tokens += usage["total_tokens"]
            saw_total = True
        if isinstance(usage.get("cost_estimate_usd"), (int, float)):
            estimated_cost += float(usage["cost_estimate_usd"])
            saw_cost = True
        if isinstance(section.get("duration_seconds"), (int, float)):
            total_duration += float(section["duration_seconds"])
    manifest.setdefault("totals", {})
    manifest["totals"].update(
        {
            "total_run_duration_seconds": round(total_duration, 3) if total_duration else None,
            "estimated_cost_usd": round(estimated_cost, 6) if saw_cost else None,
            "input_tokens": input_tokens if saw_input else None,
            "output_tokens": output_tokens if saw_output else None,
            "total_tokens": total_tokens if saw_total else None,
        }
    )
