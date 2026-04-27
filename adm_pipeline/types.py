"""Typed helpers for ADM pipeline data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonObject = dict[str, Any]


@dataclass(slots=True)
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(slots=True)
class ProviderUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_estimate_usd: float | None = None


@dataclass(slots=True)
class SectionResult:
    section_id: str
    raw_response: JsonObject
    normalized: JsonObject
    usage: ProviderUsage = field(default_factory=ProviderUsage)
    response_id: str | None = None


@dataclass(slots=True)
class CritiqueIssue:
    section_id: str
    severity: str
    code: str
    message: str
