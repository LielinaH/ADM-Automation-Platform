"""Deterministic mock provider for local smoke tests."""

from __future__ import annotations

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.sections import build_mock_section
from adm_pipeline.types import ProviderUsage, SectionResult


class MockProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        normalized = build_mock_section(section_packet)
        raw_response = {
            "provider": "mock",
            "model": self.config.model,
            "repair_notes": repair_notes or [],
            "content": normalized,
        }
        usage = ProviderUsage(input_tokens=0, output_tokens=0, total_tokens=0, cost_estimate_usd=0.0)
        return SectionResult(section_id=section_packet["section_id"], raw_response=raw_response, normalized=normalized, usage=usage)
