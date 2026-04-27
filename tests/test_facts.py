from pathlib import Path
import unittest

from adm_pipeline.facts import build_section_inputs, compute_facts
from adm_pipeline.utils import read_json


ROOT = Path(__file__).resolve().parents[1]


class FactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")

    def test_facts_are_internally_consistent(self) -> None:
        facts = compute_facts(self.payload)
        self.assertAlmostEqual(facts["tcv_5y_usd"], self.payload["annual_adm_spend_usd"] * 5)
        self.assertAlmostEqual(sum(facts["investment_by_year_usd"]), facts["transformation_investment_total_usd"], places=1)
        self.assertAlmostEqual(
            facts["cumulative_business_value_usd"] - facts["transformation_investment_total_usd"],
            facts["net_value_created_usd"],
            places=2,
        )

    def test_section_packets_cover_all_sections(self) -> None:
        facts = compute_facts(self.payload)
        packets = build_section_inputs(self.payload, facts)
        self.assertEqual(len(packets), 12)
        self.assertIn("sec01", packets)
        self.assertIn("sec12", packets)


if __name__ == "__main__":
    unittest.main()
