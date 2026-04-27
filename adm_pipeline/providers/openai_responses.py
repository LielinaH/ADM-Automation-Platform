"""Hosted OpenAI Responses API adapter."""

from __future__ import annotations

import json
import os

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.types import ProviderUsage, SectionResult


class OpenAIResponsesProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("openai package is required for the openai_responses provider") from exc
        api_key = os.environ.get(config.api_key_env or "OPENAI_API_KEY")
        if not api_key and not config.base_url:
            raise RuntimeError(f"Environment variable {config.api_key_env or 'OPENAI_API_KEY'} is required")
        self._client = OpenAI(api_key=api_key or "local-api-key", base_url=config.base_url)

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        response = self._client.responses.create(
            model=self.config.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": _build_prompt(prompt, repair_notes),
                        }
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": f"{section_packet['section_id']}_output",
                    "schema": schema,
                    "strict": True,
                }
            },
            reasoning={"effort": self.config.reasoning_effort},
            temperature=self.config.temperature,
            timeout=self.config.timeout_seconds,
        )
        payload = response.model_dump()
        text_output = _extract_output_text(payload)
        normalized = json.loads(text_output)
        usage = ProviderUsage(
            input_tokens=(payload.get("usage") or {}).get("input_tokens"),
            output_tokens=(payload.get("usage") or {}).get("output_tokens"),
            total_tokens=(payload.get("usage") or {}).get("total_tokens"),
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
    if not repair_notes:
        return prompt
    notes = "\n".join(f"- {note}" for note in repair_notes)
    return f"{prompt}\n\nRepair requirements:\n{notes}"


def _extract_output_text(payload: dict) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                return text
    raise RuntimeError("OpenAI response did not contain output text")
