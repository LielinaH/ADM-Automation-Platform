"""Financial facts computation and section packet preparation."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from adm_pipeline.constants import BENCHMARK_STYLE_VERSION, DISPOSITIONS, PROMPT_SET_VERSION, SECTION_CONFIG_BY_ID, SECTION_SCHEMA_VERSION
from adm_pipeline.types import JsonObject
from adm_pipeline.utils import average, sha256_json


def blended_rate(rate_card: JsonObject, mix_pct: JsonObject) -> float:
    return (
        rate_card["onshore"] * mix_pct["onshore"] / 100.0
        + rate_card["nearshore"] * mix_pct["nearshore"] / 100.0
        + rate_card["offshore"] * mix_pct["offshore"] / 100.0
    )


def auto_disposition(app: JsonObject) -> str:
    age = app["age_years"]
    readiness = app["cloud_readiness"]
    criticality = app["business_criticality"]
    integrations = app["integration_count"]
    fit = app.get("functional_fit", "Medium")
    change = app.get("change_frequency", "Medium")

    if age >= 15 and readiness == "Low" and fit in {"Low", "Medium"} and criticality != "High":
        return "Retire"
    if age <= 5 and readiness == "High" and integrations <= 6 and fit == "High":
        return "Retain"
    if criticality == "High" and integrations >= 15 and age >= 8:
        return "Rearchitect"
    if readiness == "High" and fit == "High" and change == "High":
        return "Refactor"
    if readiness == "Low" and integrations <= 10:
        return "Rehost"
    if readiness == "Medium" and fit in {"Medium", "High"}:
        return "Replatform"
    return "Retain"


def compute_facts(client: JsonObject) -> JsonObject:
    spend = client["annual_adm_spend_usd"]
    fa = client["financial_assumptions"]
    years = fa["contract_years"]

    tcv_5y_usd = spend * years
    transformation_investment_total_usd = tcv_5y_usd * (fa["transformation_investment_pct_of_tcv"] / 100.0)
    investment_by_year_usd = [
        transformation_investment_total_usd * (weight / 100.0)
        for weight in fa["investment_curve_pct"]
    ]

    labor_spend = spend * (fa["labor_share_pct_of_adm"] / 100.0)
    current_blended = blended_rate(fa["rate_card_usd_per_hour"], fa["current_delivery_mix_pct"])
    target_blended = blended_rate(fa["rate_card_usd_per_hour"], fa["target_delivery_mix_pct"])
    annual_workforce_savings = labor_spend * ((current_blended - target_blended) / current_blended)

    annual_legacy_savings = 0.0
    disposition_counts: Counter[str] = Counter()
    run_cost_by_disposition: dict[str, float] = defaultdict(float)
    for app in client["apps"]:
        disposition = app.get("disposition") or auto_disposition(app)
        rate_pct = fa["legacy_savings_rate_by_disposition_pct"][disposition] / 100.0
        annual_legacy_savings += app["annual_run_cost_usd"] * rate_pct
        disposition_counts[disposition] += 1
        run_cost_by_disposition[disposition] += app["annual_run_cost_usd"]

    annual_productivity_value = (
        labor_spend
        * (fa.get("automation_productivity_uplift_pct", 0) / 100.0)
        * (fa.get("productivity_value_capture_pct", 0) / 100.0)
    )
    annual_resilience_value = spend * (fa.get("resilience_value_pct_of_adm", 0) / 100.0)

    work_curve = [value / 100.0 for value in fa["benefit_ramp_curves_pct"]["workforce"]]
    legacy_curve = [value / 100.0 for value in fa["benefit_ramp_curves_pct"]["legacy"]]
    prod_curve = [value / 100.0 for value in fa["benefit_ramp_curves_pct"]["productivity"]]
    res_curve = [value / 100.0 for value in fa["benefit_ramp_curves_pct"]["resilience"]]

    yearly_business_value_usd: list[float] = []
    yearly_investment_net_usd: list[float] = []
    for index in range(years):
        value = (
            annual_workforce_savings * work_curve[index]
            + annual_legacy_savings * legacy_curve[index]
            + annual_productivity_value * prod_curve[index]
            + annual_resilience_value * res_curve[index]
        )
        yearly_business_value_usd.append(round(value, 2))
        yearly_investment_net_usd.append(round(value - investment_by_year_usd[index], 2))

    cumulative_business_value_usd = round(sum(yearly_business_value_usd), 2)
    net_value_created_usd = round(cumulative_business_value_usd - transformation_investment_total_usd, 2)
    roi_pct = round((net_value_created_usd / transformation_investment_total_usd) * 100.0, 2)

    apps = client["apps"]
    total_app_run_cost_usd = round(sum(app["annual_run_cost_usd"] for app in apps), 2)
    dependency_edges = sum(len(app["dependency_metadata"]) for app in apps)
    business_unit_costs: dict[str, float] = defaultdict(float)
    app_count_by_business_unit: Counter[str] = Counter()
    hosting_mix: Counter[str] = Counter()
    host_location_mix: Counter[str] = Counter()
    for app in apps:
        business_unit_costs[app["business_unit"]] += app["annual_run_cost_usd"]
        app_count_by_business_unit[app["business_unit"]] += 1
        hosting_mix[app["hosting_environment_type"]] += 1
        host_location_mix[app["host_location_code"]] += 1

    staffing_mix = {
        center["location_code"]: center["fte_share_pct"]
        for center in client["delivery_centers"]
    }

    facts = {
        "client_id": client["client_id"],
        "client_input_sha256": sha256_json(client),
        "annual_adm_spend_usd": round(spend, 2),
        "tcv_5y_usd": round(tcv_5y_usd, 2),
        "transformation_investment_total_usd": round(transformation_investment_total_usd, 2),
        "investment_by_year_usd": [round(value, 2) for value in investment_by_year_usd],
        "workforce_savings_rate_arbitrage_cumulative_usd": round(annual_workforce_savings * sum(work_curve), 2),
        "legacy_cost_reduction_cumulative_usd": round(annual_legacy_savings * sum(legacy_curve), 2),
        "productivity_value_cumulative_usd": round(annual_productivity_value * sum(prod_curve), 2),
        "resilience_value_cumulative_usd": round(annual_resilience_value * sum(res_curve), 2),
        "yearly_business_value_usd": yearly_business_value_usd,
        "yearly_investment_net_usd": yearly_investment_net_usd,
        "cumulative_business_value_usd": cumulative_business_value_usd,
        "net_value_created_usd": net_value_created_usd,
        "roi_pct": roi_pct,
        "disposition_counts": {disposition: disposition_counts.get(disposition, 0) for disposition in DISPOSITIONS},
        "run_cost_by_disposition_usd": {disposition: round(run_cost_by_disposition.get(disposition, 0.0), 2) for disposition in DISPOSITIONS},
        "apps_in_scope": len(apps),
        "business_units_in_scope": len(client["business_units"]),
        "delivery_center_count": len(client["delivery_centers"]),
        "average_app_age_years": round(average([float(app["age_years"]) for app in apps]), 2),
        "total_app_run_cost_usd": total_app_run_cost_usd,
        "run_cost_to_adm_ratio": round(total_app_run_cost_usd / spend, 4),
        "app_count_by_business_unit": dict(app_count_by_business_unit),
        "run_cost_by_business_unit_usd": {key: round(value, 2) for key, value in business_unit_costs.items()},
        "hosting_environment_mix": dict(hosting_mix),
        "host_location_mix": dict(host_location_mix),
        "delivery_center_staffing_mix_pct": staffing_mix,
        "dependency_edges": dependency_edges,
        "average_dependencies_per_app": round(dependency_edges / len(apps), 2),
        "workforce_savings_annual_usd": round(annual_workforce_savings, 2),
        "legacy_savings_annual_usd": round(annual_legacy_savings, 2),
        "productivity_value_annual_usd": round(annual_productivity_value, 2),
        "resilience_value_annual_usd": round(annual_resilience_value, 2),
    }
    return facts


def build_section_inputs(client: JsonObject, facts: JsonObject) -> dict[str, JsonObject]:
    sections: dict[str, JsonObject] = {}
    phase_summaries = _build_phase_summaries(client, facts)
    for section_id in SECTION_CONFIG_BY_ID:
        config = SECTION_CONFIG_BY_ID[section_id]
        sections[section_id] = {
            "section_id": section_id,
            "section_title": config.title,
            "phase": config.phase,
            "versions": {
                "schema_version": client["schema_version"],
                "prompt_set_version": PROMPT_SET_VERSION,
                "benchmark_style_version": BENCHMARK_STYLE_VERSION,
                "section_schema_version": SECTION_SCHEMA_VERSION,
            },
            "client": _slice_client_for_section(section_id, client),
            "facts": _slice_facts_for_section(section_id, facts),
            "phase_context": phase_summaries[config.phase],
            "quality_guardrails": {
                "benchmark": "Cisco ADM HTML benchmark",
                "all_numbers_must_come_from_supplied_inputs": True,
                "no_html_output": True,
            },
        }
    return sections


def _build_phase_summaries(client: JsonObject, facts: JsonObject) -> dict[str, JsonObject]:
    return {
        "Diagnose": {
            "business_problem": client["narrative_context"]["pain_points"],
            "estate_scope": {
                "apps": facts["apps_in_scope"],
                "business_units": facts["business_units_in_scope"],
                "competitors": len(client["competitors"]),
            },
        },
        "Future State": {
            "transformation_targets": client["targets"],
            "top_execution_assumptions": client["narrative_context"]["execution_assumptions"][:3],
        },
        "Value Story": {
            "roi_pct": facts["roi_pct"],
            "cumulative_business_value_usd": facts["cumulative_business_value_usd"],
            "investment_by_year_usd": facts["investment_by_year_usd"],
        },
        "Close": {
            "delivery_center_count": facts["delivery_center_count"],
            "benchmark_summary": {
                "legacy_cost_reduction_pct": client["targets"]["legacy_cost_reduction_pct"],
                "innovation_budget_shift_pct": client["targets"]["innovation_budget_shift_pct"],
            },
        },
    }


def _slice_client_for_section(section_id: str, client: JsonObject) -> JsonObject:
    shared = {
        "company": client["company"],
        "narrative_context": client["narrative_context"],
        "targets": client["targets"],
        "financial_assumptions": client["financial_assumptions"],
    }
    if section_id in {"sec01", "sec08", "sec09", "sec10", "sec12"}:
        shared["delivery_centers"] = client["delivery_centers"]
    if section_id in {"sec02", "sec07", "sec10"}:
        shared["business_units"] = client["business_units"]
    if section_id in {"sec04", "sec11"}:
        shared["competitors"] = client["competitors"]
    if section_id in {"sec07", "sec12"}:
        shared["data_estate"] = client["data_estate"]
    if section_id in {"sec05", "sec09"}:
        shared["current_state_metrics"] = client["narrative_context"]["current_state_metrics"]
    if section_id == "sec03":
        shared["apps"] = [
            {
                "id": app["id"],
                "name": app["name"],
                "business_unit": app["business_unit"],
                "disposition": app["disposition"],
                "annual_run_cost_usd": app["annual_run_cost_usd"],
                "host_location_label": app["host_location_label"],
                "dependency_count": len(app["dependency_metadata"]),
            }
            for app in client["apps"]
        ]
    if section_id == "sec06":
        shared["apps"] = [
            {
                "name": app["name"],
                "business_unit": app["business_unit"],
                "disposition": app["disposition"],
                "migration_blockers": app["migration_blockers"][:2],
                "dependency_count": len(app["dependency_metadata"]),
            }
            for app in client["apps"]
        ]
    return shared


def _slice_facts_for_section(section_id: str, facts: JsonObject) -> JsonObject:
    common = {
        "annual_adm_spend_usd": facts["annual_adm_spend_usd"],
        "apps_in_scope": facts["apps_in_scope"],
        "business_units_in_scope": facts["business_units_in_scope"],
        "delivery_center_count": facts["delivery_center_count"],
        "average_app_age_years": facts["average_app_age_years"],
        "disposition_counts": facts["disposition_counts"],
    }
    if section_id in {"sec01", "sec08", "sec09", "sec11", "sec12"}:
        common.update(
            {
                "tcv_5y_usd": facts["tcv_5y_usd"],
                "transformation_investment_total_usd": facts["transformation_investment_total_usd"],
                "cumulative_business_value_usd": facts["cumulative_business_value_usd"],
                "net_value_created_usd": facts["net_value_created_usd"],
                "roi_pct": facts["roi_pct"],
                "investment_by_year_usd": facts["investment_by_year_usd"],
                "yearly_business_value_usd": facts["yearly_business_value_usd"],
            }
        )
    if section_id in {"sec02", "sec03", "sec06", "sec07"}:
        common.update(
            {
                "dependency_edges": facts["dependency_edges"],
                "run_cost_by_business_unit_usd": facts["run_cost_by_business_unit_usd"],
                "app_count_by_business_unit": facts["app_count_by_business_unit"],
                "hosting_environment_mix": facts["hosting_environment_mix"],
                "average_dependencies_per_app": facts["average_dependencies_per_app"],
                "total_app_run_cost_usd": facts["total_app_run_cost_usd"],
                "run_cost_to_adm_ratio": facts["run_cost_to_adm_ratio"],
            }
        )
    if section_id == "sec08":
        common.update(
            {
                "workforce_savings_rate_arbitrage_cumulative_usd": facts["workforce_savings_rate_arbitrage_cumulative_usd"],
                "legacy_cost_reduction_cumulative_usd": facts["legacy_cost_reduction_cumulative_usd"],
                "productivity_value_cumulative_usd": facts["productivity_value_cumulative_usd"],
                "resilience_value_cumulative_usd": facts["resilience_value_cumulative_usd"],
            }
        )
    if section_id in {"sec10", "sec12"}:
        common["delivery_center_staffing_mix_pct"] = facts["delivery_center_staffing_mix_pct"]
    return common
