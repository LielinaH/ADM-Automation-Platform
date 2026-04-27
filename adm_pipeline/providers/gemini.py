"""Gemini provider via direct REST API."""

from __future__ import annotations

import json
import os
from urllib import error, request

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.types import ProviderUsage, SectionResult
from adm_pipeline.utils import parse_json_response_text


class GeminiProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        env_name = config.api_key_env or "GEMINI_API_KEY"
        api_key = os.environ.get(env_name)
        if not api_key:
            raise RuntimeError(f"Environment variable {env_name} is required")
        base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self._endpoint = f"{base_url}/models/{config.model}:generateContent"
        self._api_key = api_key

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": _build_prompt(prompt, repair_notes),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_output_tokens,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc
        text_output = response_payload["candidates"][0]["content"]["parts"][0]["text"]
        normalized = parse_json_response_text(text_output)
        usage_payload = response_payload.get("usageMetadata", {})
        usage = ProviderUsage(
            input_tokens=usage_payload.get("promptTokenCount"),
            output_tokens=usage_payload.get("candidatesTokenCount"),
            total_tokens=usage_payload.get("totalTokenCount"),
            cost_estimate_usd=None,
        )
        return SectionResult(
            section_id=section_packet["section_id"],
            raw_response=response_payload,
            normalized=normalized,
            usage=usage,
            response_id=response_payload.get("responseId"),
        )


def _build_prompt(prompt: str, repair_notes: list[str] | None) -> str:
    if not repair_notes:
        return prompt
    notes = "\n".join(f"- {note}" for note in repair_notes)
    return f"{prompt}\n\nRepair requirements:\n{notes}"
