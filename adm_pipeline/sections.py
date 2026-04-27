"""Section schema helpers and deterministic mock section generation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from adm_pipeline.constants import SECTION_CONFIG_BY_ID
from adm_pipeline.types import JsonObject, ValidationReport
from adm_pipeline.utils import format_currency, format_pct


def section_json_schema(section_id: str) -> JsonObject:
    config = SECTION_CONFIG_BY_ID[section_id]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "section_id": {"type": "string", "const": section_id},
            "title": {"type": "string", "const": config.title},
            "phase": {"type": "string", "const": config.phase},
            "summary": {"type": "string"},
            "narrative": {"type": "array", "items": {"type": "string"}},
            "kpi_cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                        "subtitle": {"type": "string"},
                        "fact_key": {"type": "string"},
                    },
                    "required": ["label", "value", "subtitle", "fact_key"],
                },
            },
            "tables": {"type": "array"},
            "cards": {"type": "array"},
            "chart": {"type": ["object", "null"]},
            "matrix": {"type": ["object", "null"]},
            "timeline": {"type": "array"},
            "delivery_cards": {"type": "array"},
            "callouts": {"type": "array", "items": {"type": "string"}},
            "fact_refs": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "required_widgets": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "section_id",
            "title",
            "phase",
            "summary",
            "narrative",
            "kpi_cards",
            "tables",
            "cards",
            "chart",
            "matrix",
            "timeline",
            "delivery_cards",
            "callouts",
            "fact_refs",
            "evidence_refs",
            "required_widgets",
        ],
    }


def validate_section_payload(section_id: str, payload: JsonObject) -> ValidationReport:
    report = ValidationReport()
    config = SECTION_CONFIG_BY_ID[section_id]
    if payload.get("section_id") != section_id:
        report.errors.append(f"{section_id} payload has wrong section_id")
    if payload.get("title") != config.title:
        report.errors.append(f"{section_id} payload has wrong title")
    if payload.get("phase") != config.phase:
        report.errors.append(f"{section_id} payload has wrong phase")
    if not payload.get("summary"):
        report.errors.append(f"{section_id} summary must be non-empty")
    if not payload.get("narrative"):
        report.errors.append(f"{section_id} narrative must be non-empty")
    missing_widgets = sorted(set(config.required_widgets) - set(payload.get("required_widgets", [])))
    if missing_widgets:
        report.errors.append(f"{section_id} is missing required widgets: {', '.join(missing_widgets)}")
    return report


def build_mock_section(packet: JsonObject) -> JsonObject:
    section_id = packet["section_id"]
    builders = {
        "sec01": _section_executive_summary,
        "sec02": _section_portfolio_analysis,
        "sec03": _section_app_inventory,
        "sec04": _section_competitive_benchmarking,
        "sec05": _section_ai_transformation,
        "sec06": _section_modernization_factory,
        "sec07": _section_cloud_data,
        "sec08": _section_financials,
        "sec09": _section_execution_roadmap,
        "sec10": _section_delivery_centers,
        "sec11": _section_benchmarking_summary,
        "sec12": _section_partnership_overview,
    }
    return builders[section_id](packet)


def _base_section(packet: JsonObject) -> JsonObject:
    config = SECTION_CONFIG_BY_ID[packet["section_id"]]
    return {
        "section_id": config.identifier,
        "title": config.title,
        "phase": config.phase,
        "summary": "",
        "narrative": [],
        "kpi_cards": [],
        "tables": [],
        "cards": [],
        "chart": None,
        "matrix": None,
        "timeline": [],
        "delivery_cards": [],
        "callouts": [],
        "fact_refs": [],
        "evidence_refs": [],
        "required_widgets": list(config.required_widgets),
    }


def _section_executive_summary(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    company = packet["client"]["company"]
    facts = packet["facts"]
    targets = packet["client"]["targets"]
    section["summary"] = (
        f"{company['name']} can shift a {format_currency(facts['annual_adm_spend_usd'])} annual ADM estate "
        f"from legacy sustainment toward faster digital execution and better operating leverage."
    )
    section["narrative"] = [
        (
            f"The Northstar estate spans {facts['apps_in_scope']} business applications across "
            f"{facts['business_units_in_scope']} business units, with an average age of {facts['average_app_age_years']} years."
        ),
        (
            f"With a five-year transformation investment of {format_currency(facts['transformation_investment_total_usd'])}, "
            f"the modeled business value reaches {format_currency(facts['cumulative_business_value_usd'])} and a target ROI of {format_pct(facts['roi_pct'])}."
        ),
    ]
    section["kpi_cards"] = [
        _kpi("Total Program Investment", facts["transformation_investment_total_usd"], "5-Year transformation spend", "transformation_investment_total_usd"),
        _kpi("Cumulative Business Value", facts["cumulative_business_value_usd"], "All modeled value streams", "cumulative_business_value_usd"),
        _kpi("Target ROI", facts["roi_pct"], "Net value / investment", "roi_pct", formatter="pct"),
    ]
    section["callouts"] = [
        f"Legacy cost reduction target: {targets['legacy_cost_reduction_pct']}%",
        f"Cloud migration target: {targets['cloud_migration_pct']}%",
        f"Innovation budget shift target: {targets['innovation_budget_shift_pct']}%",
        f"Release-frequency improvement target: {targets['release_frequency_improvement_pct']}%",
    ]
    section["fact_refs"] = [
        "transformation_investment_total_usd",
        "cumulative_business_value_usd",
        "roi_pct",
        "apps_in_scope",
    ]
    return section


def _section_portfolio_analysis(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    apps = packet["client"]["apps"]
    facts = packet["facts"]
    bu_cards = []
    for name, count in facts["app_count_by_business_unit"].items():
        bu_cards.append(
            {
                "title": name,
                "metric": f"{count} apps",
                "detail": format_currency(facts["run_cost_by_business_unit_usd"][name]),
            }
        )
    section["summary"] = "Portfolio shape by business unit, run-cost concentration, and application age."
    section["narrative"] = [
        (
            f"The portfolio carries {facts['dependency_edges']} declared dependency edges, averaging "
            f"{facts['average_dependencies_per_app']} dependencies per application."
        ),
        (
            f"Total application run cost is {format_currency(facts['total_app_run_cost_usd'])}, representing "
            f"{round(facts['run_cost_to_adm_ratio'] * 100, 1)}% of annual ADM spend."
        ),
    ]
    section["cards"] = bu_cards
    section["chart"] = {
        "widget": "portfolio-chart",
        "title": "Portfolio Distribution by Business Unit",
        "series": [
            {"label": name, "value": count}
            for name, count in facts["app_count_by_business_unit"].items()
        ],
    }
    section["fact_refs"] = [
        "dependency_edges",
        "average_dependencies_per_app",
        "total_app_run_cost_usd",
        "run_cost_to_adm_ratio",
        "app_count_by_business_unit",
    ]
    return section


def _section_app_inventory(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    apps = packet["client"]["apps"]
    section["summary"] = "Complete inventory of in-scope applications with modernization signals."
    section["narrative"] = [
        "The inventory preserves business ownership, hosting placement, disposition choice, and dependency metadata for downstream roadmap and delivery planning."
    ]
    section["tables"] = [
        {
            "widget": "app-table",
            "title": "Application Inventory",
            "columns": ["ID", "Application", "Business Unit", "Disposition", "Run Cost", "Hosting", "Dependencies"],
            "rows": [
                [
                    app["id"],
                    app["name"],
                    app["business_unit"],
                    app["disposition"],
                    format_currency(app["annual_run_cost_usd"]),
                    app["host_location_label"],
                    str(len(app["dependency_metadata"])),
                ]
                for app in apps
            ],
        }
    ]
    section["fact_refs"] = ["apps_in_scope"]
    return section


def _section_competitive_benchmarking(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    competitors = packet["client"]["competitors"]
    section["summary"] = "Public-signal comparison against Northstar's most relevant retail competitors."
    section["narrative"] = [
        "This section keeps the comparison evidence-backed by tying every competitor card to explicit public signals and structured competitor metrics.",
    ]
    section["cards"] = [
        {
            "widget": "competitor-cards",
            "title": competitor["name"],
            "segment": competitor["segment"],
            "strengths": competitor["public_strengths"],
            "gaps": competitor["assumed_client_gap"],
            "signals": competitor["evidence_signals"],
        }
        for competitor in competitors
    ]
    section["tables"] = [
        {
            "title": "Competitor Evidence Metrics",
            "columns": ["Competitor", "Metric", "Value", "Year", "Evidence Type", "Confidence"],
            "rows": [
                [
                    competitor["name"],
                    metric["metric_name"],
                    metric["metric_value"],
                    str(metric["metric_year"]),
                    metric["evidence_type"],
                    metric["confidence"],
                ]
                for competitor in competitors
                for metric in competitor["competitor_metrics"]
            ],
        }
    ]
    section["evidence_refs"] = [
        f"{competitor['name']}:{metric['metric_name']}"
        for competitor in competitors
        for metric in competitor["competitor_metrics"]
    ]
    return section


def _section_ai_transformation(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    context = packet["client"]["narrative_context"]
    metrics = packet["client"]["current_state_metrics"]
    section["summary"] = "AI transformation priorities mapped to current operational bottlenecks."
    section["narrative"] = [
        "Northstar's AI agenda is anchored in execution bottlenecks that already exist in release flow, incident recovery, inventory latency, and customer identity quality.",
        "The transformation sequence prioritizes shared enablement first so later modernization waves inherit stronger observability, support automation, and data foundations.",
    ]
    section["cards"] = [
        {
            "widget": "transformation-pillars",
            "title": priority,
            "detail": metrics[index % len(metrics)]["name"],
        }
        for index, priority in enumerate(context["strategic_priorities"])
    ]
    section["evidence_refs"] = [metric["name"] for metric in metrics]
    return section


def _section_modernization_factory(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    apps = packet["client"]["apps"]
    grouped: dict[str, list[str]] = defaultdict(list)
    for app in apps:
        grouped[app["disposition"]].append(app["name"])
    section["summary"] = "Six-column modernization matrix and factory sequencing foundation."
    section["narrative"] = [
        "Dispositions are grouped into the benchmark's six required lanes so roadmap planning, financial savings, and delivery ownership stay aligned.",
    ]
    section["matrix"] = {
        "widget": "modernization-matrix",
        "columns": list(grouped.keys()),
        "items": grouped,
    }
    section["fact_refs"] = ["disposition_counts"]
    return section


def _section_cloud_data(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    data_estate = packet["client"]["data_estate"]
    facts = packet["facts"]
    section["summary"] = "Cloud hosting direction and data-governance posture required to support omnichannel modernization."
    section["narrative"] = [
        "The cloud strategy has to balance legacy on-prem DC concentration with selective cloud-native acceleration in the customer-facing estate.",
        "The data strategy is constrained less by platform absence than by ownership fragmentation and stale batch interfaces.",
    ]
    section["cards"] = [
        {
            "widget": "cloud-data-cards",
            "title": "Hosting Mix",
            "detail": ", ".join(f"{key}: {value}" for key, value in facts["hosting_environment_mix"].items()),
        },
        {
            "widget": "cloud-data-cards",
            "title": "Governance Model",
            "detail": data_estate["governance_model"],
        },
    ]
    section["tables"] = [
        {
            "title": "Domain Ownership",
            "columns": ["Domain", "Owner Role"],
            "rows": [[owner["domain"], owner["owner_role"]] for owner in data_estate["domain_owners"]],
        }
    ]
    section["fact_refs"] = ["hosting_environment_mix"]
    section["evidence_refs"] = [owner["domain"] for owner in data_estate["domain_owners"]]
    return section


def _section_financials(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    facts = packet["facts"]
    client = packet["client"]
    section["summary"] = "Code-computed financial profile for the five-year transformation."
    section["narrative"] = [
        "All values in this section are generated by the facts engine, not by the language model.",
        "The benchmark narrative centers on investment, value creation, and return, so the charts and KPI cards use the same computed inputs as the critique and QA passes.",
    ]
    section["kpi_cards"] = [
        _kpi("5-Year TCV", facts["tcv_5y_usd"], "Annual ADM spend x 5 years", "tcv_5y_usd"),
        _kpi("Transformation Investment", facts["transformation_investment_total_usd"], "ROI denominator", "transformation_investment_total_usd"),
        _kpi("Net Value Created", facts["net_value_created_usd"], "Business value less investment", "net_value_created_usd"),
        _kpi("Target ROI", facts["roi_pct"], "Net value / investment", "roi_pct", formatter="pct"),
    ]
    section["chart"] = {
        "widget": "financial-chart",
        "title": "5-Year Investment vs Value",
        "series": [
            {"label": f"Year {index + 1}", "investment": investment, "value": value}
            for index, (investment, value) in enumerate(
                zip(facts["investment_by_year_usd"], facts["yearly_business_value_usd"], strict=True)
            )
        ],
    }
    section["tables"] = [
        {
            "title": "Value Stream Mix",
            "columns": ["Value Stream", "5-Year Value"],
            "rows": [
                ["Workforce savings", format_currency(facts["workforce_savings_rate_arbitrage_cumulative_usd"])],
                ["Legacy cost reduction", format_currency(facts["legacy_cost_reduction_cumulative_usd"])],
                ["Productivity value", format_currency(facts["productivity_value_cumulative_usd"])],
                ["Resilience value", format_currency(facts["resilience_value_cumulative_usd"])],
            ],
        }
    ]
    section["fact_refs"] = [
        "tcv_5y_usd",
        "transformation_investment_total_usd",
        "net_value_created_usd",
        "roi_pct",
        "investment_by_year_usd",
        "yearly_business_value_usd",
    ]
    return section


def _section_execution_roadmap(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    facts = packet["facts"]
    section["summary"] = "Year-by-year execution sequencing aligned to value realization."
    section["narrative"] = [
        "The roadmap uses the benchmark's year-based structure and links each wave to investment phasing, platform dependencies, and target-state readiness assumptions.",
    ]
    year_labels = [
        "Foundation",
        "Acceleration",
        "Scale",
        "Optimization",
        "Optimization",
    ]
    section["timeline"] = [
        {
            "year": f"Year {index + 1}",
            "phase": year_labels[index],
            "investment": format_currency(facts["investment_by_year_usd"][index]),
            "business_value": format_currency(facts["yearly_business_value_usd"][index]),
            "milestone": milestone,
        }
        for index, milestone in enumerate(
            [
                "Stabilize identity, pricing, observability, and operating governance.",
                "Launch modernization factory waves and expand shared engineering platform services.",
                "Scale cloud migration, delivery-mix transition, and event-driven operating flows.",
                "Consolidate legacy estates and industrialize ongoing optimization.",
                "Lock in innovation-budget shift and mature the steady-state operating model.",
            ]
        )
    ]
    section["fact_refs"] = ["investment_by_year_usd", "yearly_business_value_usd"]
    return section


def _section_delivery_centers(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    centers = packet["client"]["delivery_centers"]
    section["summary"] = "Delivery-center architecture and staffing mix for the transformation program."
    section["narrative"] = [
        "The delivery layout is intentionally weighted toward offshore engineering scale while preserving nearshore and leadership coverage where business-facing collaboration matters most."
    ]
    section["delivery_cards"] = [
        {
            "widget": "delivery-layout",
            "title": center["location"],
            "subtitle": center["type"],
            "fte_share_pct": center["fte_share_pct"],
            "primary_scope": center["primary_scope"],
            "governance_owner_role": center["governance_owner_role"],
            "wave_ownership": center["wave_ownership"],
        }
        for center in centers
    ]
    section["fact_refs"] = ["delivery_center_staffing_mix_pct"]
    return section


def _section_benchmarking_summary(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    facts = packet["facts"]
    targets = packet["client"]["targets"]
    section["summary"] = "Synthesis of Northstar's competitive position and modeled post-transformation improvement."
    section["narrative"] = [
        "The summary consolidates competitive signals, transformation targets, and the financial thesis into a concise benchmark-informed position for executive review.",
    ]
    section["cards"] = [
        {
            "widget": "benchmark-summary",
            "title": "Legacy Reduction",
            "metric": f"{targets['legacy_cost_reduction_pct']}%",
            "detail": "Modeled estate simplification target",
        },
        {
            "widget": "benchmark-summary",
            "title": "Innovation Shift",
            "metric": f"{targets['innovation_budget_shift_pct']}%",
            "detail": "Budget rebalance toward strategic work",
        },
        {
            "widget": "benchmark-summary",
            "title": "ROI",
            "metric": format_pct(facts["roi_pct"]),
            "detail": "Modeled return against transformation investment",
        },
    ]
    section["fact_refs"] = ["roi_pct", "cumulative_business_value_usd"]
    section["evidence_refs"] = ["benchmark-summary-synthesis"]
    return section


def _section_partnership_overview(packet: JsonObject) -> JsonObject:
    section = _base_section(packet)
    client = packet["client"]
    section["summary"] = "Operating model, governance cadence, and partnership structure for sustained delivery."
    section["narrative"] = [
        "The partnership model closes the ADM by translating the delivery architecture and roadmap into explicit governance, staffing, and execution rhythms.",
        "Northstar's execution assumptions imply a weekly design authority cadence and a monthly architecture review rhythm during active modernization waves.",
    ]
    section["cards"] = [
        {
            "widget": "partnership-overview",
            "title": "Governance Cadence",
            "detail": "Weekly design authority, monthly architecture review board",
        },
        {
            "widget": "partnership-overview",
            "title": "Delivery Mix Target",
            "detail": "35% onshore / 10% nearshore / 55% offshore",
        },
    ]
    section["callouts"] = client["narrative_context"]["execution_assumptions"][:4]
    section["fact_refs"] = ["delivery_center_count"]
    return section


def _kpi(label: str, value: float, subtitle: str, fact_key: str, formatter: str = "currency") -> JsonObject:
    if formatter == "pct":
        rendered = format_pct(value)
    else:
        rendered = format_currency(value)
    return {"label": label, "value": rendered, "subtitle": subtitle, "fact_key": fact_key}
