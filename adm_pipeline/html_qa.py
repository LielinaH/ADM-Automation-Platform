"""Final rendered HTML QA checks."""

from __future__ import annotations

import re
from pathlib import Path

from adm_pipeline.constants import FINAL_QA_FILENAME, PLACEHOLDER_PATTERNS, REQUIRED_SECTION_IDS, SECTIONS
from adm_pipeline.run_state import load_manifest, save_manifest
from adm_pipeline.utils import read_text, write_json


def qa_rendered_html(run_dir: Path, *, html_path: Path | None = None) -> dict:
    manifest = load_manifest(run_dir)
    path = html_path or Path(manifest["artifacts"]["final_html"])
    html = read_text(path)
    failures: list[str] = []
    warnings: list[str] = []

    section_ids = _find_section_ids(html)
    for section_id in REQUIRED_SECTION_IDS:
        if section_id not in section_ids:
            failures.append(f"Missing section anchor id {section_id}")

    href_targets = re.findall(r'href="#([^"]+)"', html)
    for section_id in REQUIRED_SECTION_IDS:
        if section_id not in href_targets:
            failures.append(f"Sidebar link missing href for {section_id}")

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern in html:
            failures.append(f"Found unresolved placeholder pattern {pattern!r}")

    if re.search(r'@import\s+url\(', html, re.IGNORECASE):
        failures.append("External CSS import found")
    if re.search(r'<link\b', html, re.IGNORECASE):
        failures.append("External link tag found")
    if re.search(r'\b(?:src|href)=["\']https?://', html, re.IGNORECASE):
        failures.append("External http/https dependency found")

    for section in SECTIONS:
        for widget in section.required_widgets:
            if f'data-widget="{widget}"' not in html:
                failures.append(f"Missing required widget {widget}")
            if f'data-widget="{widget}" data-filled="true"' not in html and f'data-filled="true" data-widget="{widget}"' not in html:
                failures.append(f"Widget {widget} is not marked filled")

    if 'data-action="print-report"' not in html or "window.print()" not in html:
        failures.append("Export / print affordance is missing")

    report = {
        "status": "pass" if not failures else "fail",
        "html_path": str(path),
        "failures": failures,
        "warnings": warnings,
    }
    write_json(run_dir / "final" / FINAL_QA_FILENAME, report)
    manifest.setdefault("step_status", {})["qa_html"] = report["status"]
    save_manifest(run_dir, manifest)
    return report


def _find_section_ids(html: str) -> set[str]:
    return set(re.findall(r'<section[^>]+id="([^"]+)"', html, re.IGNORECASE))
