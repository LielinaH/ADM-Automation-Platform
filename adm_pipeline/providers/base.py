"""Base provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from adm_pipeline.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MODEL,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)
from adm_pipeline.types import JsonObject, SectionResult


@dataclass(slots=True)
class ProviderConfig:
    provider_kind: str
    model: str = DEFAULT_MODEL
    base_url: str | None = None
    api_key_env: str | None = None
    temperature: float = DEFAULT_TEMPERATURE
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    profile_name: str | None = None


class SectionProvider(Protocol):
    config: ProviderConfig

    def generate_section(
        self,
        section_packet: JsonObject,
        schema: JsonObject,
        prompt: str,
        *,
        repair_notes: list[str] | None = None,
    ) -> SectionResult:
        ...
