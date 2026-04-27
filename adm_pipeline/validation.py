"""Validation for frozen ADM ingress payloads."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from adm_pipeline.constants import (
    CRITICALITY_LEVELS,
    DELIVERY_CENTER_TYPES,
    DEPENDENCY_TYPES,
    DISPOSITIONS,
    EVIDENCE_TYPES,
    HOSTING_ENVIRONMENT_TYPES,
    SCHEMA_VERSION,
)
from adm_pipeline.types import JsonObject, ValidationReport

TOP_LEVEL_KEYS = {
    "schema_version",
    "client_id",
    "company",
    "narrative_context",
    "annual_adm_spend_usd",
    "business_units",
    "apps",
    "competitors",
    "data_estate",
    "delivery_centers",
    "targets",
    "financial_assumptions",
}


def validate_client_payload(payload: JsonObject) -> ValidationReport:
    report = ValidationReport()
    _check_keys("root", payload, TOP_LEVEL_KEYS, TOP_LEVEL_KEYS, report)
    if payload.get("schema_version") != SCHEMA_VERSION:
        report.errors.append(f"schema_version must equal {SCHEMA_VERSION!r}")
    if not payload.get("client_id"):
        report.errors.append("client_id must be non-empty")

    _validate_company(payload.get("company"), report)
    _validate_narrative_context(payload.get("narrative_context"), report)
    _validate_business_units(payload.get("business_units"), report)
    _validate_apps(payload.get("apps"), payload.get("business_units"), report)
    _validate_competitors(payload.get("competitors"), report)
    _validate_data_estate(payload.get("data_estate"), report)
    _validate_delivery_centers(payload.get("delivery_centers"), report)
    _validate_targets(payload.get("targets"), report)
    _validate_financial_assumptions(payload.get("financial_assumptions"), report)
    _validate_cross_references(payload, report)
    _quality_checks(payload, report)
    return report


def _check_keys(
    path: str,
    value: Any,
    allowed: set[str],
    required: Iterable[str],
    report: ValidationReport,
) -> None:
    if not isinstance(value, dict):
        report.errors.append(f"{path} must be an object")
        return
    keys = set(value.keys())
    extra = sorted(keys - allowed)
    missing = sorted(set(required) - keys)
    if extra:
        report.errors.append(f"{path} contains unsupported keys: {', '.join(extra)}")
    if missing:
        report.errors.append(f"{path} is missing required keys: {', '.join(missing)}")


def _require_non_empty_list(path: str, value: Any, report: ValidationReport) -> list[Any]:
    if not isinstance(value, list) or not value:
        report.errors.append(f"{path} must be a non-empty array")
        return []
    return value


def _require_enum(path: str, value: Any, allowed: set[str], report: ValidationReport) -> None:
    if value not in allowed:
        report.errors.append(f"{path} must be one of {sorted(allowed)}")


def _require_percent(path: str, value: Any, report: ValidationReport) -> None:
    if not isinstance(value, (int, float)) or value < 0 or value > 100:
        report.errors.append(f"{path} must be a number in [0, 100]")


def _validate_company(company: Any, report: ValidationReport) -> None:
    allowed = {
        "name",
        "industry",
        "subsector",
        "headquarters",
        "operating_regions",
        "employees",
        "annual_revenue_usd",
        "summary",
    }
    required = {
        "name",
        "industry",
        "headquarters",
        "operating_regions",
        "employees",
        "annual_revenue_usd",
        "summary",
    }
    _check_keys("company", company, allowed, required, report)
    if isinstance(company, dict):
        _require_non_empty_list("company.operating_regions", company.get("operating_regions"), report)


def _validate_narrative_context(context: Any, report: ValidationReport) -> None:
    allowed = {
        "strategic_priorities",
        "pain_points",
        "regulatory_context",
        "operating_model_notes",
        "current_state_metrics",
        "execution_assumptions",
    }
    required = {
        "strategic_priorities",
        "pain_points",
        "regulatory_context",
        "current_state_metrics",
        "execution_assumptions",
    }
    _check_keys("narrative_context", context, allowed, required, report)
    if not isinstance(context, dict):
        return
    for key in ("strategic_priorities", "pain_points", "regulatory_context", "current_state_metrics", "execution_assumptions"):
        _require_non_empty_list(f"narrative_context.{key}", context.get(key), report)
    metric_allowed = {
        "name",
        "baseline_value",
        "baseline_unit",
        "target_value",
        "target_unit",
        "scope",
        "evidence_type",
        "evidence_note",
        "confidence",
    }
    for index, metric in enumerate(context.get("current_state_metrics", [])):
        _check_keys(f"narrative_context.current_state_metrics[{index}]", metric, metric_allowed, metric_allowed, report)
        if isinstance(metric, dict):
            _require_enum(
                f"narrative_context.current_state_metrics[{index}].evidence_type",
                metric.get("evidence_type"),
                EVIDENCE_TYPES,
                report,
            )
            _require_enum(
                f"narrative_context.current_state_metrics[{index}].confidence",
                metric.get("confidence"),
                CRITICALITY_LEVELS,
                report,
            )


def _validate_business_units(units: Any, report: ValidationReport) -> None:
    items = _require_non_empty_list("business_units", units, report)
    allowed = {"name", "owner_role", "core_capabilities", "kpis"}
    metric_allowed = {
        "name",
        "baseline_value",
        "baseline_unit",
        "target_value",
        "target_unit",
        "evidence_type",
        "evidence_note",
        "confidence",
    }
    for index, unit in enumerate(items):
        _check_keys(f"business_units[{index}]", unit, allowed, allowed, report)
        if not isinstance(unit, dict):
            continue
        _require_non_empty_list(f"business_units[{index}].core_capabilities", unit.get("core_capabilities"), report)
        _require_non_empty_list(f"business_units[{index}].kpis", unit.get("kpis"), report)
        for metric_index, metric in enumerate(unit.get("kpis", [])):
            _check_keys(f"business_units[{index}].kpis[{metric_index}]", metric, metric_allowed, metric_allowed, report)
            if isinstance(metric, dict):
                _require_enum(
                    f"business_units[{index}].kpis[{metric_index}].evidence_type",
                    metric.get("evidence_type"),
                    EVIDENCE_TYPES,
                    report,
                )
                _require_enum(
                    f"business_units[{index}].kpis[{metric_index}].confidence",
                    metric.get("confidence"),
                    CRITICALITY_LEVELS,
                    report,
                )


def _validate_apps(apps: Any, units: Any, report: ValidationReport) -> None:
    items = _require_non_empty_list("apps", apps, report)
    unit_names = {unit.get("name") for unit in units or [] if isinstance(unit, dict)}
    allowed = {
        "id",
        "name",
        "business_unit",
        "capability",
        "age_years",
        "tech_stack",
        "annual_run_cost_usd",
        "business_criticality",
        "integration_count",
        "cloud_readiness",
        "disposition",
        "functional_fit",
        "customer_facing",
        "change_frequency",
        "data_sensitivity",
        "hosting_model",
        "hosting_environment_type",
        "host_location_code",
        "host_location_label",
        "dependency_metadata",
        "migration_blockers",
        "vendor_lock_in",
        "release_constraint",
    }
    required = allowed
    dependency_allowed = {"depends_on", "dependency_type", "dependency_criticality"}
    for index, app in enumerate(items):
        _check_keys(f"apps[{index}]", app, allowed, required, report)
        if not isinstance(app, dict):
            continue
        _require_non_empty_list(f"apps[{index}].tech_stack", app.get("tech_stack"), report)
        _require_non_empty_list(f"apps[{index}].dependency_metadata", app.get("dependency_metadata"), report)
        _require_non_empty_list(f"apps[{index}].migration_blockers", app.get("migration_blockers"), report)
        if app.get("business_unit") not in unit_names:
            report.errors.append(f"apps[{index}].business_unit must match a declared business unit")
        for enum_key in (
            "business_criticality",
            "cloud_readiness",
            "functional_fit",
            "change_frequency",
            "data_sensitivity",
            "vendor_lock_in",
        ):
            _require_enum(f"apps[{index}].{enum_key}", app.get(enum_key), CRITICALITY_LEVELS, report)
        _require_enum(
            f"apps[{index}].hosting_environment_type",
            app.get("hosting_environment_type"),
            HOSTING_ENVIRONMENT_TYPES,
            report,
        )
        _require_enum(f"apps[{index}].disposition", app.get("disposition"), set(DISPOSITIONS), report)
        seen_dependencies: set[str] = set()
        for dep_index, dependency in enumerate(app.get("dependency_metadata", [])):
            _check_keys(
                f"apps[{index}].dependency_metadata[{dep_index}]",
                dependency,
                dependency_allowed,
                dependency_allowed,
                report,
            )
            if not isinstance(dependency, dict):
                continue
            dep_target = dependency.get("depends_on")
            if dep_target in seen_dependencies:
                report.errors.append(
                    f"apps[{index}].dependency_metadata contains duplicate depends_on value {dep_target}"
                )
            seen_dependencies.add(dep_target)
            _require_enum(
                f"apps[{index}].dependency_metadata[{dep_index}].dependency_type",
                dependency.get("dependency_type"),
                DEPENDENCY_TYPES,
                report,
            )
            _require_enum(
                f"apps[{index}].dependency_metadata[{dep_index}].dependency_criticality",
                dependency.get("dependency_criticality"),
                CRITICALITY_LEVELS,
                report,
            )


def _validate_competitors(competitors: Any, report: ValidationReport) -> None:
    items = _require_non_empty_list("competitors", competitors, report)
    allowed = {
        "name",
        "segment",
        "public_strengths",
        "assumed_client_gap",
        "evidence_note",
        "evidence_signals",
        "competitor_metrics",
    }
    metric_allowed = {
        "metric_name",
        "metric_value",
        "metric_year",
        "evidence_type",
        "evidence_note",
        "confidence",
    }
    for index, competitor in enumerate(items):
        _check_keys(f"competitors[{index}]", competitor, allowed, allowed, report)
        if not isinstance(competitor, dict):
            continue
        _require_non_empty_list(f"competitors[{index}].public_strengths", competitor.get("public_strengths"), report)
        _require_non_empty_list(f"competitors[{index}].assumed_client_gap", competitor.get("assumed_client_gap"), report)
        _require_non_empty_list(f"competitors[{index}].evidence_signals", competitor.get("evidence_signals"), report)
        metrics = _require_non_empty_list(f"competitors[{index}].competitor_metrics", competitor.get("competitor_metrics"), report)
        for metric_index, metric in enumerate(metrics):
            _check_keys(f"competitors[{index}].competitor_metrics[{metric_index}]", metric, metric_allowed, metric_allowed, report)
            if isinstance(metric, dict):
                _require_enum(
                    f"competitors[{index}].competitor_metrics[{metric_index}].evidence_type",
                    metric.get("evidence_type"),
                    EVIDENCE_TYPES,
                    report,
                )
                _require_enum(
                    f"competitors[{index}].competitor_metrics[{metric_index}].confidence",
                    metric.get("confidence"),
                    CRITICALITY_LEVELS,
                    report,
                )


def _validate_data_estate(data_estate: Any, report: ValidationReport) -> None:
    allowed = {
        "domains",
        "current_platforms",
        "integration_pain_points",
        "governance_gaps",
        "governance_model",
        "domain_owners",
        "data_quality_pain_points",
    }
    required = {
        "domains",
        "current_platforms",
        "integration_pain_points",
        "governance_model",
        "domain_owners",
        "data_quality_pain_points",
    }
    _check_keys("data_estate", data_estate, allowed, required, report)
    if not isinstance(data_estate, dict):
        return
    for key in ("domains", "current_platforms", "integration_pain_points", "domain_owners", "data_quality_pain_points"):
        _require_non_empty_list(f"data_estate.{key}", data_estate.get(key), report)
    owner_allowed = {"domain", "owner_role"}
    for index, owner in enumerate(data_estate.get("domain_owners", [])):
        _check_keys(f"data_estate.domain_owners[{index}]", owner, owner_allowed, owner_allowed, report)


def _validate_delivery_centers(delivery_centers: Any, report: ValidationReport) -> None:
    items = _require_non_empty_list("delivery_centers", delivery_centers, report)
    allowed = {
        "location",
        "location_code",
        "type",
        "primary_roles",
        "strategic_reason",
        "timezone_overlap_hours",
        "fte_share_pct",
        "wave_ownership",
        "governance_owner_role",
        "primary_scope",
    }
    required = {
        "location",
        "location_code",
        "type",
        "primary_roles",
        "strategic_reason",
        "fte_share_pct",
        "wave_ownership",
        "governance_owner_role",
        "primary_scope",
    }
    for index, center in enumerate(items):
        _check_keys(f"delivery_centers[{index}]", center, allowed, required, report)
        if not isinstance(center, dict):
            continue
        _require_non_empty_list(f"delivery_centers[{index}].primary_roles", center.get("primary_roles"), report)
        _require_non_empty_list(f"delivery_centers[{index}].wave_ownership", center.get("wave_ownership"), report)
        _require_enum(f"delivery_centers[{index}].type", center.get("type"), DELIVERY_CENTER_TYPES, report)
        _require_percent(f"delivery_centers[{index}].fte_share_pct", center.get("fte_share_pct"), report)


def _validate_targets(targets: Any, report: ValidationReport) -> None:
    required = {
        "cloud_migration_pct",
        "legacy_cost_reduction_pct",
        "release_frequency_improvement_pct",
        "change_failure_rate_reduction_pct",
        "innovation_budget_shift_pct",
    }
    _check_keys("targets", targets, required, required, report)
    if not isinstance(targets, dict):
        return
    for key, value in targets.items():
        _require_percent(f"targets.{key}", value, report)


def _validate_financial_assumptions(financials: Any, report: ValidationReport) -> None:
    allowed = {
        "contract_years",
        "transformation_investment_pct_of_tcv",
        "investment_curve_pct",
        "labor_share_pct_of_adm",
        "current_delivery_mix_pct",
        "target_delivery_mix_pct",
        "rate_card_usd_per_hour",
        "automation_productivity_uplift_pct",
        "productivity_value_capture_pct",
        "resilience_value_pct_of_adm",
        "legacy_savings_rate_by_disposition_pct",
        "benefit_ramp_curves_pct",
        "assumption_provenance",
    }
    required = allowed
    _check_keys("financial_assumptions", financials, allowed, required, report)
    if not isinstance(financials, dict):
        return
    if financials.get("contract_years") != 5:
        report.errors.append("financial_assumptions.contract_years must equal 5")
    for key in (
        "transformation_investment_pct_of_tcv",
        "labor_share_pct_of_adm",
        "automation_productivity_uplift_pct",
        "productivity_value_capture_pct",
        "resilience_value_pct_of_adm",
    ):
        _require_percent(f"financial_assumptions.{key}", financials.get(key), report)
    _validate_mix_object("financial_assumptions.current_delivery_mix_pct", financials.get("current_delivery_mix_pct"), report)
    _validate_mix_object("financial_assumptions.target_delivery_mix_pct", financials.get("target_delivery_mix_pct"), report)
    _validate_rate_card("financial_assumptions.rate_card_usd_per_hour", financials.get("rate_card_usd_per_hour"), report)
    _validate_disposition_rates(
        "financial_assumptions.legacy_savings_rate_by_disposition_pct",
        financials.get("legacy_savings_rate_by_disposition_pct"),
        report,
    )
    _validate_benefit_curves("financial_assumptions.benefit_ramp_curves_pct", financials.get("benefit_ramp_curves_pct"), report)
    _validate_assumption_provenance(financials.get("assumption_provenance"), report)
    curve = financials.get("investment_curve_pct")
    if not isinstance(curve, list) or len(curve) != 5:
        report.errors.append("financial_assumptions.investment_curve_pct must contain 5 values")
    else:
        for index, value in enumerate(curve):
            _require_percent(f"financial_assumptions.investment_curve_pct[{index}]", value, report)
        if round(sum(curve), 3) != 100:
            report.errors.append("financial_assumptions.investment_curve_pct must sum to 100")


def _validate_mix_object(path: str, mix: Any, report: ValidationReport) -> None:
    allowed = {"onshore", "nearshore", "offshore"}
    _check_keys(path, mix, allowed, allowed, report)
    if not isinstance(mix, dict):
        return
    total = 0.0
    for key in allowed:
        value = mix.get(key)
        _require_percent(f"{path}.{key}", value, report)
        if isinstance(value, (int, float)):
            total += float(value)
    if round(total, 3) != 100:
        report.errors.append(f"{path} must sum to 100")


def _validate_rate_card(path: str, rate_card: Any, report: ValidationReport) -> None:
    allowed = {"onshore", "nearshore", "offshore"}
    _check_keys(path, rate_card, allowed, allowed, report)


def _validate_disposition_rates(path: str, rates: Any, report: ValidationReport) -> None:
    allowed = set(DISPOSITIONS)
    _check_keys(path, rates, allowed, allowed, report)
    if not isinstance(rates, dict):
        return
    for key in allowed:
        _require_percent(f"{path}.{key}", rates.get(key), report)


def _validate_benefit_curves(path: str, curves: Any, report: ValidationReport) -> None:
    allowed = {"workforce", "legacy", "productivity", "resilience"}
    required = allowed
    _check_keys(path, curves, allowed, required, report)
    if not isinstance(curves, dict):
        return
    for key in required:
        values = curves.get(key)
        if not isinstance(values, list) or len(values) != 5:
            report.errors.append(f"{path}.{key} must contain 5 values")
            continue
        for index, value in enumerate(values):
            _require_percent(f"{path}.{key}[{index}]", value, report)


def _validate_assumption_provenance(items: Any, report: ValidationReport) -> None:
    assumptions = _require_non_empty_list("financial_assumptions.assumption_provenance", items, report)
    allowed = {"assumption_name", "value", "assumption_basis", "confidence", "owner_function"}
    for index, item in enumerate(assumptions):
        _check_keys(f"financial_assumptions.assumption_provenance[{index}]", item, allowed, allowed, report)
        if isinstance(item, dict):
            _require_enum(
                f"financial_assumptions.assumption_provenance[{index}].confidence",
                item.get("confidence"),
                CRITICALITY_LEVELS,
                report,
            )


def _validate_cross_references(payload: JsonObject, report: ValidationReport) -> None:
    app_ids = [app.get("id") for app in payload.get("apps", []) if isinstance(app, dict)]
    counts = Counter(app_ids)
    duplicates = sorted(identifier for identifier, count in counts.items() if count > 1)
    if duplicates:
        report.errors.append(f"apps contain duplicate ids: {', '.join(duplicates)}")
    business_units = [unit.get("name") for unit in payload.get("business_units", []) if isinstance(unit, dict)]
    unit_counts = Counter(business_units)
    duplicate_units = sorted(name for name, count in unit_counts.items() if count > 1)
    if duplicate_units:
        report.errors.append(f"business_units contain duplicate names: {', '.join(duplicate_units)}")
    valid_ids = set(app_ids)
    for app_index, app in enumerate(payload.get("apps", [])):
        if not isinstance(app, dict):
            continue
        for dep_index, dependency in enumerate(app.get("dependency_metadata", [])):
            if dependency.get("depends_on") not in valid_ids:
                report.errors.append(
                    f"apps[{app_index}].dependency_metadata[{dep_index}].depends_on must reference an existing app id"
                )


def _quality_checks(payload: JsonObject, report: ValidationReport) -> None:
    apps = payload.get("apps", [])
    business_units = payload.get("business_units", [])
    competitors = payload.get("competitors", [])
    data_domains = payload.get("data_estate", {}).get("domains", [])
    delivery_centers = payload.get("delivery_centers", [])
    if len(apps) < 12:
        report.warnings.append("Fewer than 12 apps reduces benchmark fidelity")
    if len(business_units) < 4:
        report.warnings.append("Fewer than 4 business units reduces organization realism")
    if len(competitors) < 3:
        report.warnings.append("Fewer than 3 competitors weakens benchmarking")
    if len(data_domains) < 5:
        report.warnings.append("Fewer than 5 data domains weakens cloud/data sections")
    if len(delivery_centers) < 3:
        report.warnings.append("Fewer than 3 delivery centers weakens delivery architecture")
    if competitors:
        for index, competitor in enumerate(competitors):
            metrics = competitor.get("competitor_metrics", []) if isinstance(competitor, dict) else []
            if len(metrics) < 2:
                report.warnings.append(f"competitors[{index}] has fewer than 2 competitor_metrics")
    low_confidence = 0
    evidence_items = 0
    for metric in payload.get("narrative_context", {}).get("current_state_metrics", []):
        evidence_items += 1
        if metric.get("confidence") == "Low":
            low_confidence += 1
    for unit in business_units:
        for metric in unit.get("kpis", []):
            evidence_items += 1
            if metric.get("confidence") == "Low":
                low_confidence += 1
    for competitor in competitors:
        for metric in competitor.get("competitor_metrics", []):
            evidence_items += 1
            if metric.get("confidence") == "Low":
                low_confidence += 1
    for item in payload.get("financial_assumptions", {}).get("assumption_provenance", []):
        evidence_items += 1
        if item.get("confidence") == "Low":
            low_confidence += 1
    if evidence_items and (low_confidence / evidence_items) > 0.25:
        report.warnings.append("More than 25% of evidence-bearing items are low confidence")
