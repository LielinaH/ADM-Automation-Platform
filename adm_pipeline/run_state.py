"""Run directory and manifest helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adm_pipeline.constants import (
    BENCHMARK_STYLE_VERSION,
    FACTS_FILENAME,
    FINAL_QA_FILENAME,
    GLOBAL_CRITIQUE_FILENAME,
    PROMPT_SET_VERSION,
    REPAIR_ACTIONS_FILENAME,
    RUN_MANIFEST_FILENAME,
    SCHEMA_VERSION,
    SECTION_SCHEMA_VERSION,
)
from adm_pipeline.utils import ensure_dir, read_json, utc_now_iso, write_json


def init_run_layout(run_dir: Path) -> dict[str, Path]:
    paths = {
        "run": ensure_dir(run_dir),
        "section_inputs": ensure_dir(run_dir / "section_inputs"),
        "sections": ensure_dir(run_dir / "sections"),
        "critique": ensure_dir(run_dir / "critique"),
        "final": ensure_dir(run_dir / "final"),
    }
    return paths


def manifest_path(run_dir: Path) -> Path:
    return run_dir / RUN_MANIFEST_FILENAME


def load_manifest(run_dir: Path) -> dict[str, Any]:
    path = manifest_path(run_dir)
    if path.exists():
        return read_json(path)
    return {}


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    manifest.setdefault("versions", {})
    manifest["versions"].update(
        {
            "schema_version": SCHEMA_VERSION,
            "prompt_set_version": PROMPT_SET_VERSION,
            "benchmark_style_version": BENCHMARK_STYLE_VERSION,
            "section_schema_version": SECTION_SCHEMA_VERSION,
        }
    )
    manifest.setdefault("updated_at", utc_now_iso())
    manifest["updated_at"] = utc_now_iso()
    write_json(manifest_path(run_dir), manifest)


def init_manifest(
    run_dir: Path,
    *,
    client_id: str,
    provider_kind: str,
    model: str,
    input_path: Path,
    scenario_mode: str,
) -> dict[str, Any]:
    manifest = {
        "client_id": client_id,
        "input_path": str(input_path),
        "provider": {"kind": provider_kind, "model": model},
        "scenario_mode": scenario_mode,
        "created_at": utc_now_iso(),
        "sections": {},
        "step_status": {},
        "totals": {
            "total_run_duration_seconds": None,
            "estimated_cost_usd": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        },
        "artifacts": {
            "facts": str(run_dir / FACTS_FILENAME),
            "global_critique": str(run_dir / "critique" / GLOBAL_CRITIQUE_FILENAME),
            "repair_actions": str(run_dir / "critique" / REPAIR_ACTIONS_FILENAME),
            "final_html": str(run_dir / "final" / f"{client_id}.html"),
            "final_qa": str(run_dir / "final" / FINAL_QA_FILENAME),
        },
    }
    save_manifest(run_dir, manifest)
    return manifest
