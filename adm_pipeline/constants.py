"""Shared constants and section metadata for the ADM pipeline."""

from __future__ import annotations

from dataclasses import dataclass

SCHEMA_VERSION = "2.0"
PROMPT_SET_VERSION = "northstar-adm-v1"
BENCHMARK_STYLE_VERSION = "cisco-html-v1"
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

REQUIRED_SECTION_IDS = tuple(f"sec{i:02d}" for i in range(1, 13))
PLACEHOLDER_PATTERNS = ("TODO", "{{", "}}", "null", "undefined")


@dataclass(frozen=True, slots=True)
class SectionConfig:
    identifier: str
    title: str
    phase: str
    nav_group: str
    required_widgets: tuple[str, ...]


SECTIONS: tuple[SectionConfig, ...] = (
    SectionConfig("sec01", "Executive Summary", "Diagnose", "Strategy & Insight", ("kpi-grid", "hero-callout")),
    SectionConfig("sec02", "Portfolio Analysis", "Diagnose", "Strategy & Insight", ("portfolio-chart", "portfolio-cards")),
    SectionConfig("sec03", "App Inventory", "Diagnose", "Strategy & Insight", ("app-table",)),
    SectionConfig("sec04", "Competitive Benchmarking", "Diagnose", "Strategy & Insight", ("competitor-cards",)),
    SectionConfig("sec05", "AI Transformation Strategy", "Future State", "The Solution", ("transformation-pillars",)),
    SectionConfig("sec06", "Modernization Roadmap / Factory", "Future State", "The Solution", ("modernization-matrix",)),
    SectionConfig("sec07", "Cloud & Data Strategy", "Future State", "The Solution", ("cloud-data-cards",)),
    SectionConfig("sec08", "Financials", "Value Story", "Execution & Value", ("financial-kpis", "financial-chart")),
    SectionConfig("sec09", "Execution Roadmap", "Value Story", "Execution & Value", ("roadmap-timeline",)),
    SectionConfig("sec10", "Delivery Center Architecture", "Value Story", "Execution & Value", ("delivery-layout",)),
    SectionConfig("sec11", "Benchmarking Summary", "Close", "Execution & Value", ("benchmark-summary",)),
    SectionConfig("sec12", "Partnership Overview", "Close", "Execution & Value", ("partnership-overview",)),
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
