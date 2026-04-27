from pathlib import Path
import unittest

from adm_pipeline.provider_profiles import load_profiles, resolve_profile


ROOT = Path(__file__).resolve().parents[1]


class ProviderProfileTests(unittest.TestCase):
    def test_profiles_file_loads(self) -> None:
        payload = load_profiles(ROOT / "config" / "providers.json")
        self.assertIn("profiles", payload)
        self.assertIn("mock-local", payload["profiles"])

    def test_default_mock_profile_resolves(self) -> None:
        profile = resolve_profile(profile_name="mock-local", config_path=ROOT / "config" / "providers.json", overrides={})
        self.assertEqual(profile.provider_kind, "mock")
        self.assertEqual(profile.profile_name, "mock-local")


if __name__ == "__main__":
    unittest.main()
