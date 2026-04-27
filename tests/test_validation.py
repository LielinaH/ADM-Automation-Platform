from pathlib import Path
import unittest

from adm_pipeline.utils import read_json
from adm_pipeline.validation import validate_client_payload


ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def test_northstar_payload_is_valid(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        report = validate_client_payload(payload)
        self.assertTrue(report.ok, report.errors)

    def test_forbidden_app_dependencies_field_fails(self) -> None:
        payload = read_json(ROOT / "inputs" / "clients" / "northstar-retail.json")
        payload["apps"][0]["app_dependencies"] = ["APP-002"]
        report = validate_client_payload(payload)
        self.assertFalse(report.ok)
        self.assertTrue(any("unsupported keys" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
