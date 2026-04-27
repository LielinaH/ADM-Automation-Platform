"""LM Studio provider via OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.types import ProviderUsage, SectionResult


class LMStudioProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        if self.config.base_url is None:
            self.config.base_url = "http://127.0.0.1:1234/v1"
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("openai package is required for the lmstudio_openai_compat provider") from exc
        self._client = OpenAI(api_key="lm-studio", base_url=self.config.base_url)

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(prompt, repair_notes),
                }
            ],
            temperature=self.config.temperature,
            timeout=self.config.timeout_seconds,
            response_format={"type": "json_object"},
        )
        payload = response.model_dump()
        text_output = payload["choices"][0]["message"]["content"]
        normalized = json.loads(text_output)
        usage_payload = payload.get("usage", {})
        usage = ProviderUsage(
            input_tokens=usage_payload.get("prompt_tokens"),
            output_tokens=usage_payload.get("completion_tokens"),
            total_tokens=usage_payload.get("total_tokens"),
            cost_estimate_usd=None,
        )
        return SectionResult(
            section_id=section_packet["section_id"],
            raw_response=payload,
            normalized=normalized,
            usage=usage,
            response_id=payload.get("id"),
        )


def _build_prompt(prompt: str, repair_notes: list[str] | None) -> str:
    schema_hint = "Return valid JSON only. Do not include markdown fences."
    if not repair_notes:
        return f"{prompt}\n\n{schema_hint}"
    notes = "\n".join(f"- {note}" for note in repair_notes)
    return f"{prompt}\n\nRepair requirements:\n{notes}\n\n{schema_hint}"
