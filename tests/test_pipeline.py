from pathlib import Path
import shutil
import unittest

from adm_pipeline.critique import critique_sections, load_generated_sections
from adm_pipeline.facts import build_section_inputs, compute_facts
from adm_pipeline.generation import generate_sections
from adm_pipeline.html_qa import qa_rendered_html
from adm_pipeline.providers import ProviderConfig
from adm_pipeline.render import render_report
from adm_pipeline.run_state import init_manifest, init_run_layout
from adm_pipeline.utils import read_json, write_json


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_mock_pipeline_end_to_end(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        facts = compute_facts(payload)
        section_inputs = build_section_inputs(payload, facts)

        temp_root = ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        temp_dir = temp_root / "pipeline-run"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            run_dir = temp_dir
            init_run_layout(run_dir)
            init_manifest(
                run_dir,
                client_id=payload["client_id"],
                provider_kind="mock",
                model="mock-model",
                profile_name="mock-local",
                input_path=(ROOT / "inputs" / "clients" / "northstar-retail.json"),
                scenario_mode="locked",
            )
            write_json(run_dir / "facts.json", facts)
            for section_id, packet in section_inputs.items():
                write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)

            provider_config = ProviderConfig(provider_kind="mock", model="mock-model")
            generate_sections(run_dir, section_inputs, provider_config)
            critique = critique_sections(run_dir, facts, load_generated_sections(run_dir))
            self.assertNotEqual(critique["status"], "fail")

            html_path = render_report(run_dir)
            self.assertTrue(html_path.exists())

            qa_report = qa_rendered_html(run_dir, html_path=html_path)
            self.assertEqual(qa_report["status"], "pass", qa_report["failures"])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_mock_pipeline_does_not_leak_northstar_into_other_client_output(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        payload["client_id"] = "atlas-grocer"
        payload["company"]["name"] = "Atlas Grocer Holdings"
        payload["company"]["summary"] = "Regional grocer with stores, digital ordering, and supply-chain operations."

        facts = compute_facts(payload)
        section_inputs = build_section_inputs(payload, facts)

        temp_root = ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        temp_dir = temp_root / "pipeline-run-generic"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            run_dir = temp_dir
            input_path = temp_root / "atlas-grocer.json"
            write_json(input_path, payload)
            init_run_layout(run_dir)
            init_manifest(
                run_dir,
                client_id=payload["client_id"],
                provider_kind="mock",
                model="mock-model",
                profile_name="mock-local",
                input_path=input_path,
                scenario_mode="locked",
            )
            write_json(run_dir / "facts.json", facts)
            for section_id, packet in section_inputs.items():
                write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)

            provider_config = ProviderConfig(provider_kind="mock", model="mock-model")
            generate_sections(run_dir, section_inputs, provider_config)
            critique_sections(run_dir, facts, load_generated_sections(run_dir))
            html_path = render_report(run_dir)
            html = html_path.read_text(encoding="utf-8")

            self.assertIn("Atlas Grocer Holdings", html)
            self.assertNotIn("Northstar", html)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            atlas_input = temp_root / "atlas-grocer.json"
            if atlas_input.exists():
                atlas_input.unlink()


if __name__ == "__main__":
    unittest.main()
