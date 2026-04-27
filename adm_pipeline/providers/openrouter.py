"""OpenRouter provider via LiteLLM."""

from __future__ import annotations

import json
import os

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.types import ProviderUsage, SectionResult


class OpenRouterProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        try:
            from litellm import completion
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("litellm package is required for the openrouter provider") from exc
        self._completion = completion
        env_key = config.api_key_env or "OPENROUTER_API_KEY"
        if not os.environ.get(env_key):
            raise RuntimeError(f"Environment variable {env_key} is required")

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        response = self._completion(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(prompt, repair_notes),
                }
            ],
            temperature=self.config.temperature,
            timeout=self.config.timeout_seconds,
        )
        payload = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        text_output = payload["choices"][0]["message"]["content"]
        normalized = json.loads(text_output)
        usage_payload = payload.get("usage", {})
        usage = ProviderUsage(
            input_tokens=usage_payload.get("prompt_tokens"),
            output_tokens=usage_payload.get("completion_tokens"),
            total_tokens=usage_payload.get("total_tokens"),
            cost_estimate_usd=usage_payload.get("response_cost"),
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
