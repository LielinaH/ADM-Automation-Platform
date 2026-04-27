"""OpenRouter provider via direct HTTP."""

from __future__ import annotations

import json
import os
from urllib import error, request

from adm_pipeline.providers.base import ProviderConfig
from adm_pipeline.types import ProviderUsage, SectionResult
from adm_pipeline.utils import parse_json_response_text


class OpenRouterProvider:
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        env_key = config.api_key_env or "OPENROUTER_API_KEY"
        api_key = os.environ.get(env_key)
        if not api_key:
            raise RuntimeError(f"Environment variable {env_key} is required")
        self._api_key = api_key
        self._endpoint = (config.base_url or "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"

    def generate_section(self, section_packet, schema, prompt, *, repair_notes=None) -> SectionResult:
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": _build_prompt(prompt, repair_notes),
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"{section_packet['section_id']}_output",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        req = request.Request(
            self._endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc
        text_output = response_payload["choices"][0]["message"]["content"]
        normalized = parse_json_response_text(text_output)
        usage_payload = response_payload.get("usage", {})
        usage = ProviderUsage(
            input_tokens=usage_payload.get("prompt_tokens"),
            output_tokens=usage_payload.get("completion_tokens"),
            total_tokens=usage_payload.get("total_tokens"),
            cost_estimate_usd=usage_payload.get("response_cost"),
        )
        return SectionResult(
            section_id=section_packet["section_id"],
            raw_response=response_payload,
            normalized=normalized,
            usage=usage,
            response_id=response_payload.get("id"),
        )


def _build_prompt(prompt: str, repair_notes: list[str] | None) -> str:
    schema_hint = "Return valid JSON only. Do not include markdown fences."
    if not repair_notes:
        return f"{prompt}\n\n{schema_hint}"
    notes = "\n".join(f"- {note}" for note in repair_notes)
    return f"{prompt}\n\nRepair requirements:\n{notes}\n\n{schema_hint}"
