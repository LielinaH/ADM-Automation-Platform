"""Shared constants and section metadata for the ADM pipeline."""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "2.0"
PROMPT_SET_VERSION = "adm-benchmark-v3"
BENCHMARK_STYLE_VERSION = "cisco-html-v2"
SECTION_SCHEMA_VERSION = "section-content-v1"

DEFAULT_PROVIDER = "openai_responses"
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_OUTPUT_TOKENS = 1800

SCENARIO_MODE_LOCKED = "locked"

RUN_MANIFEST_FILENAME = "manifest.json"
FACTS_FILENAME = "facts.json"
FINAL_QA_FILENAME = "final_qa.json"
GLOBAL_CRITIQUE_FILENAME = "global_critique.json"
REPAIR_ACTIONS_FILENAME = "repair_actions.json"
BENCHMARK_SCORE_FILENAME = "benchmark_score.json"

REQUIRED_SECTION_IDS = tuple(f"sec{i:02d}" for i in range(1, 13))
PLACEHOLDER_PATTERNS = ("TODO", "{{", "}}", "null", "undefined")


@dataclass(frozen=True, slots=True)
class SectionConfig:
    identifier: str
    title: str
    phase: str
    nav_group: str
    required_widgets: tuple[str, ...]
    benchmark_brief: str
    min_narrative_paragraphs: int = 2
    min_kpi_cards: int = 0
    min_tables: int = 0
    min_cards: int = 0
    min_callouts: int = 0
    min_timeline_items: int = 0
    min_delivery_cards: int = 0


SECTIONS: tuple[SectionConfig, ...] = (
    SectionConfig(
        "sec01",
        "Executive Summary",
        "Diagnose",
        "Strategy & Insight",
        ("kpi-grid", "hero-callout"),
        "State the estate scale, transformation thesis, ROI case, and the core execution challenge in a polished executive voice.",
        min_narrative_paragraphs=4,
        min_kpi_cards=4,
        min_callouts=4,
    ),
    SectionConfig(
        "sec02",
        "Portfolio Analysis",
        "Diagnose",
        "Strategy & Insight",
        ("portfolio-chart", "portfolio-cards"),
        "Explain cost concentration, dependency density, and business-unit skew with portfolio interpretation rather than just inventory recitation.",
        min_narrative_paragraphs=4,
        min_kpi_cards=4,
        min_cards=5,
        min_callouts=2,
    ),
    SectionConfig(
        "sec03",
        "App Inventory",
        "Diagnose",
        "Strategy & Insight",
        ("app-table",),
        "Frame the inventory as an actionable management view with summary metrics and disposition implications, not just a table dump.",
        min_narrative_paragraphs=3,
        min_kpi_cards=4,
        min_tables=1,
        min_callouts=2,
    ),
    SectionConfig(
        "sec04",
        "Competitive Benchmarking",
        "Diagnose",
        "Strategy & Insight",
        ("competitor-cards",),
        "Synthesize competitor evidence into clear comparative positioning and implications for the client's gap-closing agenda.",
        min_narrative_paragraphs=4,
        min_tables=1,
        min_cards=3,
        min_callouts=2,
    ),
    SectionConfig(
        "sec05",
        "AI Transformation Strategy",
        "Future State",
        "The Solution",
        ("transformation-pillars",),
        "Translate operational pain points into a sequenced AI agenda with explicit enablement logic and business outcomes.",
        min_narrative_paragraphs=4,
        min_cards=4,
        min_callouts=3,
    ),
    SectionConfig(
        "sec06",
        "Modernization Roadmap / Factory",
        "Future State",
        "The Solution",
        ("modernization-matrix",),
        "Use the six-lane modernization factory view to explain how dispositions convert into execution waves and savings capture.",
        min_narrative_paragraphs=4,
        min_kpi_cards=3,
        min_callouts=3,
    ),
    SectionConfig(
        "sec07",
        "Cloud & Data Strategy",
        "Future State",
        "The Solution",
        ("cloud-data-cards",),
        "Connect hosting strategy, governance, and data-domain ownership into a concrete architecture narrative with migration implications.",
        min_narrative_paragraphs=4,
        min_kpi_cards=1,
        min_tables=1,
        min_cards=2,
        min_callouts=2,
    ),
    SectionConfig(
        "sec08",
        "Financials",
        "Value Story",
        "Execution & Value",
        ("financial-kpis", "financial-chart"),
        "Interpret the five-year value case like a board-ready business case, including investment phasing and value-stream contribution.",
        min_narrative_paragraphs=4,
        min_kpi_cards=4,
        min_tables=1,
        min_callouts=3,
    ),
    SectionConfig(
        "sec09",
        "Execution Roadmap",
        "Value Story",
        "Execution & Value",
        ("roadmap-timeline",),
        "Explain why each year matters, what unlocks the next wave, and how value realization tracks the roadmap.",
        min_narrative_paragraphs=3,
        min_timeline_items=5,
        min_callouts=2,
    ),
    SectionConfig(
        "sec10",
        "Delivery Center Architecture",
        "Value Story",
        "Execution & Value",
        ("delivery-layout",),
        "Describe the operating geography, governance ownership, and work split as a deliberate delivery model rather than a staffing list.",
        min_narrative_paragraphs=3,
        min_kpi_cards=1,
        min_delivery_cards=3,
        min_callouts=2,
    ),
    SectionConfig(
        "sec11",
        "Benchmarking Summary",
        "Close",
        "Execution & Value",
        ("benchmark-summary",),
        "Close with benchmark-informed positioning that synthesizes the value thesis, gap closure, and strategic upside.",
        min_narrative_paragraphs=3,
        min_cards=3,
        min_callouts=2,
    ),
    SectionConfig(
        "sec12",
        "Partnership Overview",
        "Close",
        "Execution & Value",
        ("partnership-overview",),
        "Finish with governance rhythm, delivery commitments, and execution model confidence in a client-ready close.",
        min_narrative_paragraphs=3,
        min_kpi_cards=1,
        min_cards=2,
        min_callouts=4,
    ),
)

SECTION_CONFIG_BY_ID = {section.identifier: section for section in SECTIONS}

DELIVERY_CENTER_TYPES = {"Onshore", "Nearshore", "Offshore"}
CRITICALITY_LEVELS = {"Low", "Medium", "High"}
HOSTING_ENVIRONMENT_TYPES = {"OnPremDC", "CloudRegion", "VendorSaaSHybrid"}
EVIDENCE_TYPES = {
    "internal_assessment",
    "annual_report",
    "investor_material",
    "earnings_call",
    "industry_report",
    "strategy_model",
}
DEPENDENCY_TYPES = {
    "Identity",
    "Pricing",
    "Order",
    "Returns",
    "StoreOps",
    "POS",
    "Fulfillment",
    "Merchandising",
    "SupplyChain",
    "Loyalty",
    "Campaign",
    "DataPlatform",
    "Supplier",
}
DISPOSITIONS = ("Retire", "Retain", "Rehost", "Replatform", "Refactor", "Rearchitect")

PHASE_ORDER = ("Diagnose", "Future State", "Value Story", "Close")
