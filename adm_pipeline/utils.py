"""Utility helpers for filesystem, JSON, hashing, and formatting."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_response_text(text: str) -> Any:
    decoder = json.JSONDecoder()
    candidates = [text.strip()]
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates = [candidate.strip() for candidate in fenced if candidate.strip()] + candidates
    for candidate in candidates:
        for marker in ("{", "["):
            index = candidate.find(marker)
            if index == -1:
                continue
            try:
                value, _end = decoder.raw_decode(candidate[index:])
                return value
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("Unable to extract JSON payload", text, 0)


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(encoded).hexdigest()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def format_currency(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    if absolute >= 1_000_000_000:
        return f"{sign}${absolute / 1_000_000_000:.2f}B"
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:.2f}M"
    if absolute >= 1_000:
        return f"{sign}${absolute / 1_000:.2f}K"
    return f"{sign}${absolute:,.0f}"


def format_pct(value: float) -> str:
    return f"{value:.2f}%"


def average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)
