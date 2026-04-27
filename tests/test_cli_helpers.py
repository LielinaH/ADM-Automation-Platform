from pathlib import Path
import shutil
import unittest

from adm_pipeline.cli import _requires_live_smoke, _run_provider_smoke, _sort_available_models
from adm_pipeline.facts import build_section_inputs, compute_facts
from adm_pipeline.providers import ProviderConfig
from adm_pipeline.run_state import init_manifest, init_run_layout, load_manifest
from adm_pipeline.sections import normalize_section_payload, validate_section_payload
from adm_pipeline.utils import read_json, write_json


ROOT = Path(__file__).resolve().parents[1]


class CliHelperTests(unittest.TestCase):
    def test_gemini_models_are_ranked_with_gemma_first(self) -> None:
        models = [
            "gemini-2.5-pro",
            "gemma-4-31b-it",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
        ]
        ranked = _sort_available_models("gemini", models)
        self.assertEqual(ranked[0], "gemma-4-31b-it")
        self.assertLess(ranked.index("gemini-2.5-flash-lite"), ranked.index("gemini-2.5-pro"))

    def test_real_providers_require_smoke(self) -> None:
        self.assertFalse(_requires_live_smoke(ProviderConfig(provider_kind="mock", model="mock-model")))
        self.assertTrue(_requires_live_smoke(ProviderConfig(provider_kind="gemini", model="gemma-4-31b-it")))
        self.assertTrue(_requires_live_smoke(ProviderConfig(provider_kind="lmstudio_openai_compat", model="google/gemma-4-e2b")))

    def test_smoke_run_marks_manifest_pass_for_mock(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        facts = compute_facts(payload)
        section_inputs = build_section_inputs(payload, facts)
        temp_root = ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        run_dir = temp_root / "smoke-run"
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
        try:
            init_run_layout(run_dir)
            init_manifest(
                run_dir,
                client_id=payload["client_id"],
                provider_kind="mock",
                model="mock-model",
                profile_name="mock-local",
                input_path=ROOT / "inputs" / "clients" / "northstar-retail.json",
                scenario_mode="locked",
            )
            write_json(run_dir / "facts.json", facts)
            for section_id, packet in section_inputs.items():
                write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)

            result = _run_provider_smoke(
                run_dir,
                section_inputs,
                ProviderConfig(provider_kind="mock", model="mock-model", profile_name="mock-local"),
                section_id="sec01",
                force=False,
            )
            manifest = load_manifest(run_dir)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(manifest["step_status"]["smoke"], "pass")
            self.assertIn("mock:mock-model:sec01", manifest["smoke_tests"])
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def test_normalize_section_payload_repairs_invalid_fact_refs(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        facts = compute_facts(payload)
        section_packet = build_section_inputs(payload, facts)["sec01"]
        broken = {
            "section_id": "sec01",
            "title": "Executive Summary",
            "phase": "Diagnose",
            "summary": "Test summary",
            "narrative": ["Test narrative"],
            "kpi_cards": [
                {"label": "ROI", "value": "49.94%", "subtitle": "bad ref", "fact_key": "legacy_cost_reduction_pct"},
            ],
            "tables": [],
            "cards": [],
            "chart": None,
            "matrix": None,
            "timeline": [],
            "delivery_cards": [],
            "callouts": ["A callout"],
            "fact_refs": ["legacy_cost_reduction_pct", "roi_pct"],
            "evidence_refs": [],
            "required_widgets": ["hero-callout"],
        }
        normalized = normalize_section_payload("sec01", broken, section_packet)
        report = validate_section_payload("sec01", normalized, section_packet)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(normalized["kpi_cards"][0]["fact_key"], "transformation_investment_total_usd")
        self.assertIn("roi_pct", normalized["fact_refs"])

    def test_normalize_section_payload_repairs_incomplete_chart(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        facts = compute_facts(payload)
        section_packet = build_section_inputs(payload, facts)["sec02"]
        broken = {
            "section_id": "sec02",
            "title": "Portfolio Analysis",
            "phase": "Diagnose",
            "summary": "Portfolio summary",
            "narrative": ["One paragraph"],
            "kpi_cards": [],
            "tables": [],
            "cards": [],
            "chart": {},
            "matrix": None,
            "timeline": [],
            "delivery_cards": [],
            "callouts": [],
            "fact_refs": ["dependency_edges"],
            "evidence_refs": [],
            "required_widgets": ["portfolio-chart"],
        }
        normalized = normalize_section_payload("sec02", broken, section_packet)
        report = validate_section_payload("sec02", normalized, section_packet)
        self.assertTrue(report.ok, report.errors)
        self.assertEqual(normalized["chart"]["widget"], "portfolio-chart")

    def test_normalize_section_payload_canonicalizes_kpi_values(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        facts = compute_facts(payload)
        section_packet = build_section_inputs(payload, facts)["sec02"]
        broken = {
            "section_id": "sec02",
            "title": "Portfolio Analysis",
            "phase": "Diagnose",
            "summary": "Portfolio summary",
            "narrative": ["One paragraph"],
            "kpi_cards": [
                {"label": "Avg App Age", "value": "11", "subtitle": "Legacy profile", "fact_key": "average_app_age_years"},
                {"label": "Dependency Density", "value": "2", "subtitle": "Average", "fact_key": "average_dependencies_per_app"},
            ],
            "tables": [],
            "cards": [],
            "chart": None,
            "matrix": None,
            "timeline": [],
            "delivery_cards": [],
            "callouts": [],
            "fact_refs": ["average_app_age_years", "average_dependencies_per_app"],
            "evidence_refs": [],
            "required_widgets": ["portfolio-chart", "portfolio-cards"],
        }
        normalized = normalize_section_payload("sec02", broken, section_packet)
        self.assertEqual(normalized["kpi_cards"][0]["value"], "11.0 Years")
        self.assertEqual(normalized["kpi_cards"][1]["value"], "2.33")


if __name__ == "__main__":
    unittest.main()
