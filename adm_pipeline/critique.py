"""Critique and targeted repair for generated section payloads."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from adm_pipeline.constants import GLOBAL_CRITIQUE_FILENAME, PLACEHOLDER_PATTERNS, REPAIR_ACTIONS_FILENAME, REQUIRED_SECTION_IDS
from adm_pipeline.generation import repair_sections
from adm_pipeline.providers import ProviderConfig
from adm_pipeline.run_state import load_manifest, save_manifest
from adm_pipeline.sections import validate_section_payload
from adm_pipeline.types import CritiqueIssue, JsonObject
from adm_pipeline.utils import format_currency, format_pct, read_json, write_json


def critique_sections(run_dir: Path, facts: JsonObject, sections: dict[str, JsonObject]) -> JsonObject:
    issues: list[CritiqueIssue] = []

    for section_id in REQUIRED_SECTION_IDS:
        if section_id not in sections:
            issues.append(CritiqueIssue(section_id, "error", "missing_section", "Required section output is missing"))
            continue
        section_packet = _load_section_packet(run_dir, section_id)
        report = validate_section_payload(section_id, sections[section_id], section_packet)
        for error in report.errors:
            issues.append(CritiqueIssue(section_id, "error", "schema_invalid", error))

    issues.extend(_placeholder_issues(sections))
    issues.extend(_repetition_issues(sections))
    issues.extend(_fact_drift_issues(sections, facts))
    issues.extend(_evidence_issues(sections))
    issues.extend(_style_issues(sections))
    issues.extend(_required_content_issues(sections))

    grouped: dict[str, list[JsonObject]] = defaultdict(list)
    repair_map: dict[str, list[str]] = defaultdict(list)
    for issue in issues:
        issue_payload = {
            "section_id": issue.section_id,
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
        }
        grouped[issue.section_id].append(issue_payload)
        if issue.severity == "error":
            repair_map[issue.section_id].append(issue.message)

    report = {
        "status": "pass" if not issues else "warn" if not repair_map else "fail",
        "issue_count": len(issues),
        "issues": [grouped[section_id] for section_id in sorted(grouped)],
        "repair_candidates": {key: value for key, value in sorted(repair_map.items())},
    }
    write_json(run_dir / "critique" / GLOBAL_CRITIQUE_FILENAME, report)
    write_json(run_dir / "critique" / REPAIR_ACTIONS_FILENAME, report["repair_candidates"])

    manifest = load_manifest(run_dir)
    manifest.setdefault("step_status", {})["critique"] = report["status"]
    save_manifest(run_dir, manifest)
    return report


def run_repair_if_needed(
    run_dir: Path,
    section_inputs: dict[str, JsonObject],
    provider_config: ProviderConfig,
    critique_report: JsonObject,
) -> dict[str, JsonObject]:
    repair_map = critique_report.get("repair_candidates", {})
    repaired = repair_sections(run_dir, section_inputs, provider_config, repair_map)
    manifest = load_manifest(run_dir)
    manifest.setdefault("step_status", {})["repair"] = "pass" if not repair_map else "applied"
    save_manifest(run_dir, manifest)
    return repaired


def load_generated_sections(run_dir: Path) -> dict[str, JsonObject]:
    sections: dict[str, JsonObject] = {}
    for section_id in REQUIRED_SECTION_IDS:
        path = run_dir / "sections" / f"{section_id}.normalized.json"
        if path.exists():
            sections[section_id] = read_json(path)
    return sections


def _load_section_packet(run_dir: Path, section_id: str) -> JsonObject | None:
    path = run_dir / "section_inputs" / f"{section_id}.json"
    if path.exists():
        return read_json(path)
    return None


def _placeholder_issues(sections: dict[str, JsonObject]) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    for section_id, payload in sections.items():
        for text in _walk_strings(payload):
            if any(pattern in text for pattern in PLACEHOLDER_PATTERNS):
                issues.append(
                    CritiqueIssue(section_id, "error", "placeholder_text", f"Section contains unresolved placeholder text: {text[:120]}")
                )
    return issues


def _repetition_issues(sections: dict[str, JsonObject]) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    seen: dict[str, str] = {}
    for section_id, payload in sections.items():
        for paragraph in payload.get("narrative", []):
            key = " ".join(paragraph.lower().split())
            if len(key) < 40:
                continue
            if key in seen and seen[key] != section_id:
                issues.append(
                    CritiqueIssue(section_id, "warning", "repeated_claim", f"Narrative repeats wording from {seen[key]}")
                )
            else:
                seen[key] = section_id
    return issues


def _fact_drift_issues(sections: dict[str, JsonObject], facts: JsonObject) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    for section_id, payload in sections.items():
        for card in payload.get("kpi_cards", []):
            fact_key = card.get("fact_key")
            if not fact_key or fact_key not in facts:
                continue
            expected = _expected_rendered_fact(fact_key, facts[fact_key])
            if expected and card.get("value") != expected:
                issues.append(
                    CritiqueIssue(
                        section_id,
                        "error",
                        "numeric_drift",
                        f"KPI card {card.get('label')} should render {expected} from {fact_key}, not {card.get('value')}",
                    )
                )
        for fact_ref in payload.get("fact_refs", []):
            if fact_ref not in facts:
                issues.append(CritiqueIssue(section_id, "error", "unknown_fact_ref", f"Unknown fact reference {fact_ref}"))
    return issues


def _evidence_issues(sections: dict[str, JsonObject]) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    for section_id in ("sec04", "sec07", "sec11"):
        payload = sections.get(section_id)
        if payload and not payload.get("evidence_refs"):
            issues.append(CritiqueIssue(section_id, "error", "missing_evidence_refs", "Benchmark section must include evidence_refs"))
    return issues


def _style_issues(sections: dict[str, JsonObject]) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    for section_id, payload in sections.items():
        narrative = payload.get("narrative", [])
        joined = " ".join(narrative)
        if len(joined.strip()) < 80:
            issues.append(CritiqueIssue(section_id, "warning", "thin_narrative", "Narrative is thinner than the benchmark style"))
        if any(token in joined.lower() for token in ("i think", "maybe", "perhaps", "!", "?")):
            issues.append(CritiqueIssue(section_id, "warning", "tone_mismatch", "Narrative tone is less formal than the benchmark"))
    return issues


def _required_content_issues(sections: dict[str, JsonObject]) -> list[CritiqueIssue]:
    issues: list[CritiqueIssue] = []
    required_map = {
        "sec01": lambda payload: bool(payload.get("kpi_cards")) and bool(payload.get("callouts")),
        "sec02": lambda payload: bool(payload.get("cards")) and bool(payload.get("chart")),
        "sec03": lambda payload: bool(payload.get("tables")),
        "sec04": lambda payload: bool(payload.get("cards")) and bool(payload.get("tables")),
        "sec05": lambda payload: bool(payload.get("cards")),
        "sec06": lambda payload: bool(payload.get("matrix")),
        "sec07": lambda payload: bool(payload.get("cards")) and bool(payload.get("tables")),
        "sec08": lambda payload: bool(payload.get("kpi_cards")) and bool(payload.get("chart")),
        "sec09": lambda payload: bool(payload.get("timeline")),
        "sec10": lambda payload: bool(payload.get("delivery_cards")),
        "sec11": lambda payload: bool(payload.get("cards")),
        "sec12": lambda payload: bool(payload.get("cards")) and bool(payload.get("callouts")),
    }
    for section_id, predicate in required_map.items():
        payload = sections.get(section_id)
        if payload and not predicate(payload):
            issues.append(CritiqueIssue(section_id, "error", "missing_required_content", "Section is missing required benchmark content blocks"))
    return issues


def _expected_rendered_fact(fact_key: str, value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    if fact_key.endswith("_pct") or fact_key == "roi_pct":
        return format_pct(float(value))
    if fact_key.endswith("_usd") or "_cost_" in fact_key or fact_key.startswith("tcv_") or fact_key.startswith("annual_adm_spend"):
        return format_currency(float(value))
    if fact_key in {"apps_in_scope", "business_units_in_scope", "delivery_center_count", "dependency_edges"}:
        return str(int(value))
    if fact_key in {"average_app_age_years"}:
        return f"{float(value):.1f} Years"
    if fact_key in {"average_dependencies_per_app"}:
        return f"{float(value):.2f}"
    return None


def _walk_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_walk_strings(item))
    return found
