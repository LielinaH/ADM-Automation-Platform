"""Self-contained HTML renderer for ADM sections."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from adm_pipeline.constants import REQUIRED_SECTION_IDS, SECTIONS
from adm_pipeline.run_state import load_manifest, save_manifest
from adm_pipeline.utils import format_currency, read_json, write_text


def render_report(run_dir: Path, *, out_path: Path | None = None) -> Path:
    manifest = load_manifest(run_dir)
    client = read_json(Path(manifest["input_path"]))
    facts = read_json(run_dir / "facts.json")
    sections = {
        section_id: read_json(run_dir / "sections" / f"{section_id}.normalized.json")
        for section_id in REQUIRED_SECTION_IDS
    }
    final_path = out_path or Path(manifest["artifacts"]["final_html"])
    html = _build_html(client, facts, sections)
    write_text(final_path, html)
    manifest.setdefault("step_status", {})["render"] = "pass"
    manifest.setdefault("artifacts", {})["final_html"] = str(final_path)
    save_manifest(run_dir, manifest)
    return final_path


def _build_html(client: dict[str, Any], facts: dict[str, Any], sections: dict[str, dict[str, Any]]) -> str:
    title = f"{client['company']['name']} ADM"
    sidebar = _render_sidebar()
    body_sections = "\n".join(_render_section(sections[section.identifier], facts) for section in SECTIONS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <style>
    :root {{
      --nav-bg: #0e1d2c;
      --nav-text: #dbe7f4;
      --page-bg: #eef3f7;
      --panel: #ffffff;
      --ink: #12263a;
      --muted: #5f7283;
      --accent: #0c7abf;
      --accent-soft: #d7edf9;
      --emerald: #0b8f63;
      --amber: #f59e0b;
      --border: #d7e0e8;
      --shadow: 0 24px 60px rgba(16, 42, 67, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Aptos", "Helvetica Neue", Arial, sans-serif;
      background: radial-gradient(circle at top right, #f7fbfd 0, #eef3f7 55%, #e7edf3 100%);
      color: var(--ink);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      padding: 32px 24px;
      background: linear-gradient(180deg, #12263a 0%, #0d1824 100%);
      color: var(--nav-text);
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    .brand {{
      padding: 18px 18px 16px;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px;
      background: rgba(255,255,255,0.04);
    }}
    .brand h1 {{
      margin: 0 0 8px;
      font-size: 26px;
      line-height: 1.05;
      letter-spacing: -0.03em;
    }}
    .brand p {{
      margin: 0;
      color: rgba(219,231,244,0.82);
      font-size: 13px;
      line-height: 1.5;
    }}
    .sidebar-group-title {{
      margin: 18px 0 10px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: rgba(219,231,244,0.62);
    }}
    .sidebar a {{
      display: block;
      padding: 9px 12px;
      margin-bottom: 6px;
      border-radius: 12px;
      color: inherit;
      text-decoration: none;
      font-size: 14px;
    }}
    .sidebar a:hover {{
      background: rgba(255,255,255,0.08);
    }}
    .sidebar-footer {{
      margin-top: auto;
      display: grid;
      gap: 12px;
    }}
    .print-button {{
      border: none;
      border-radius: 14px;
      padding: 12px 14px;
      font-weight: 700;
      color: white;
      background: linear-gradient(135deg, #0c7abf 0%, #0f9dcf 100%);
      cursor: pointer;
    }}
    main {{
      padding: 36px;
      display: grid;
      gap: 28px;
    }}
    .section {{
      background: rgba(255,255,255,0.78);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(215,224,232,0.95);
      border-radius: 28px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .section-header {{
      padding: 28px 30px 18px;
      border-bottom: 1px solid rgba(215,224,232,0.85);
      background: linear-gradient(180deg, rgba(255,255,255,0.75), rgba(242,247,250,0.88));
    }}
    .section-header .eyebrow {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .section-header h2 {{
      margin: 0 0 10px;
      font-size: 32px;
      line-height: 1.06;
      letter-spacing: -0.03em;
    }}
    .section-header p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
      max-width: 880px;
    }}
    .section-body {{
      padding: 28px 30px 34px;
      display: grid;
      gap: 24px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.7fr 1fr;
      gap: 20px;
      align-items: stretch;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 22px;
    }}
    .panel h3 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: -0.02em;
    }}
    .narrative {{
      display: grid;
      gap: 12px;
    }}
    .narrative p {{
      margin: 0;
      line-height: 1.7;
      color: #264154;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }}
    .kpi-card {{
      padding: 18px;
      background: linear-gradient(180deg, #fbfdff 0%, #f3f8fb 100%);
      border: 1px solid var(--border);
      border-radius: 18px;
    }}
    .kpi-card .label {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 10px;
      font-weight: 700;
    }}
    .kpi-card .value {{
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: -0.04em;
      font-weight: 800;
    }}
    .kpi-card .subtitle {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .callouts {{
      display: grid;
      gap: 10px;
    }}
    .callout {{
      padding: 14px 16px;
      background: #f4fafc;
      border-left: 4px solid var(--accent);
      border-radius: 14px;
      color: #1f435a;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .card {{
      padding: 18px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: white;
      display: grid;
      gap: 10px;
    }}
    .card .title {{
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .card .metric {{
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.04em;
    }}
    .card ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .card li {{
      margin: 6px 0;
      color: #335066;
    }}
    .table-shell {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
      min-width: 680px;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .matrix {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
    }}
    .matrix-column {{
      background: white;
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 16px;
      min-height: 180px;
    }}
    .matrix-column h4 {{
      margin: 0 0 10px;
      font-size: 15px;
    }}
    .matrix-column ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .timeline {{
      display: grid;
      gap: 14px;
    }}
    .timeline-item {{
      display: grid;
      grid-template-columns: 130px 1fr;
      gap: 18px;
      align-items: start;
      padding: 18px;
      background: white;
      border-radius: 18px;
      border: 1px solid var(--border);
    }}
    .timeline-year {{
      font-weight: 800;
      color: var(--accent);
    }}
    .timeline-meta {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 4px;
    }}
    .svg-shell {{
      background: white;
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 16px;
    }}
    .delivery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}
    .delivery-card {{
      background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 18px;
      display: grid;
      gap: 10px;
    }}
    .delivery-card .share {{
      font-size: 26px;
      font-weight: 800;
      color: var(--emerald);
    }}
    .footer-note {{
      color: var(--muted);
      font-size: 13px;
      text-align: center;
      padding-top: 10px;
    }}
    @media (max-width: 1100px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: relative; height: auto; }}
      .hero {{ grid-template-columns: 1fr; }}
      .matrix {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      main {{ padding: 20px; }}
    }}
    @media print {{
      .sidebar {{ display: none; }}
      .layout {{ grid-template-columns: 1fr; }}
      body {{ background: white; }}
      main {{ padding: 0; }}
      .section {{ box-shadow: none; border: 1px solid #d0d7de; break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    {sidebar}
    <main>
      {body_sections}
      <div class="footer-note">Generated from structured ingress and code-computed financials. Annual ADM spend: {escape(format_currency(facts["annual_adm_spend_usd"]))}.</div>
    </main>
  </div>
  <script>
    document.querySelectorAll('.sidebar a[href^="#"]').forEach(function(link) {{
      link.addEventListener('click', function(event) {{
        var target = document.querySelector(this.getAttribute('href'));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }});
    }});
  </script>
</body>
</html>"""


def _render_sidebar() -> str:
    groups: dict[str, list[str]] = {}
    for section in SECTIONS:
        groups.setdefault(section.nav_group, []).append(
            f'<a href="#{section.identifier}">{escape(section.title)}</a>'
        )
    group_html = []
    for group_name, links in groups.items():
        group_html.append(
            f'<div><div class="sidebar-group-title">{escape(group_name)}</div>{"".join(links)}</div>'
        )
    return (
        '<aside class="sidebar">'
        '<div class="brand"><h1>ADM</h1><p>Northstar benchmark pipeline output with 12 assessment-aligned sections, critique-driven repair, and final HTML QA.</p></div>'
        + "".join(group_html)
        + '<div class="sidebar-footer"><button class="print-button" type="button" data-action="print-report" onclick="window.print()">Export / Print</button></div></aside>'
    )


def _render_section(section: dict[str, Any], facts: dict[str, Any]) -> str:
    body_parts = [
        _render_narrative(section.get("narrative", [])),
        _render_kpis(section),
        _render_cards(section),
        _render_tables(section.get("tables", [])),
        _render_chart(section.get("chart")),
        _render_matrix(section.get("matrix")),
        _render_timeline(section.get("timeline", [])),
        _render_delivery_cards(section.get("delivery_cards", [])),
        _render_callouts(section.get("callouts", [])),
        _render_fact_refs(section.get("fact_refs", []), facts),
    ]
    if section["section_id"] == "sec01":
        body = _render_hero(section, facts)
    else:
        body = "".join(part for part in body_parts if part)
    return (
        f'<section id="{escape(section["section_id"])}" class="section" data-section-id="{escape(section["section_id"])}">'
        f'<div class="section-header"><div class="eyebrow">{escape(section["phase"])}</div><h2>{escape(section["title"])}</h2><p>{escape(section["summary"])}</p></div>'
        f'<div class="section-body">{body}</div>'
        "</section>"
    )


def _render_hero(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        '<div class="hero">'
        f'<div class="panel" data-widget="hero-callout" data-filled="true"><h3>Program Thesis</h3>{_render_narrative(section.get("narrative", []))}{_render_callouts(section.get("callouts", []))}</div>'
        f'<div class="panel">{_render_kpis(section, override_widget="kpi-grid")}{_render_fact_refs(section.get("fact_refs", []), facts)}</div>'
        "</div>"
    )


def _render_narrative(paragraphs: list[str]) -> str:
    if not paragraphs:
        return ""
    return '<div class="narrative">' + "".join(f"<p>{escape(text)}</p>" for text in paragraphs) + "</div>"


def _render_kpis(section: dict[str, Any], *, override_widget: str | None = None) -> str:
    cards = section.get("kpi_cards", [])
    if not cards:
        return ""
    widget = override_widget or ("financial-kpis" if section["section_id"] == "sec08" else "kpi-grid")
    items = []
    for card in cards:
        items.append(
            '<div class="kpi-card">'
            f'<div class="label">{escape(card["label"])}</div>'
            f'<div class="value">{escape(card["value"])}</div>'
            f'<div class="subtitle">{escape(card["subtitle"])}</div>'
            "</div>"
        )
    return f'<div class="kpi-grid" data-widget="{escape(widget)}" data-filled="true">{"".join(items)}</div>'


def _render_callouts(callouts: list[str]) -> str:
    if not callouts:
        return ""
    return '<div class="callouts">' + "".join(f'<div class="callout">{escape(item)}</div>' for item in callouts) + "</div>"


def _render_cards(section: dict[str, Any]) -> str:
    cards = section.get("cards", [])
    if not cards:
        return ""
    widget = _cards_widget_name(section["section_id"])
    rendered = []
    for card in cards:
        pieces = [f'<div class="title">{escape(str(card.get("title", "")))}</div>']
        if card.get("segment"):
            pieces.append(f'<div class="subtitle">{escape(str(card["segment"]))}</div>')
        if card.get("metric"):
            pieces.append(f'<div class="metric">{escape(str(card["metric"]))}</div>')
        if card.get("detail"):
            pieces.append(f'<div>{escape(str(card["detail"]))}</div>')
        if card.get("strengths"):
            pieces.append("<strong>Public strengths</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["strengths"]) + "</ul>")
        if card.get("gaps"):
            pieces.append("<strong>Northstar gap</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["gaps"]) + "</ul>")
        if card.get("signals"):
            pieces.append("<strong>Signals</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["signals"]) + "</ul>")
        rendered.append(f'<div class="card">{"".join(pieces)}</div>')
    return f'<div class="cards" data-widget="{escape(widget)}" data-filled="true">{"".join(rendered)}</div>'


def _cards_widget_name(section_id: str) -> str:
    return {
        "sec02": "portfolio-cards",
        "sec04": "competitor-cards",
        "sec05": "transformation-pillars",
        "sec07": "cloud-data-cards",
        "sec11": "benchmark-summary",
        "sec12": "partnership-overview",
    }.get(section_id, "cards")


def _render_tables(tables: list[dict[str, Any]]) -> str:
    if not tables:
        return ""
    rendered = []
    for table in tables:
        header = "".join(f"<th>{escape(column)}</th>" for column in table["columns"])
        rows = "".join(
            "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
            for row in table["rows"]
        )
        widget_attr = f' data-widget="{escape(table["widget"])}" data-filled="true"' if table.get("widget") else ""
        rendered.append(
            f'<div class="panel table-shell"{widget_attr}><h3>{escape(table["title"])}</h3>'
            f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>"
        )
    return "".join(rendered)


def _render_chart(chart: dict[str, Any] | None) -> str:
    if not chart:
        return ""
    widget = chart.get("widget", "chart")
    if widget == "financial-chart":
        svg = _render_financial_svg(chart["series"])
    else:
        svg = _render_simple_bar_svg(chart["series"])
    return f'<div class="svg-shell" data-widget="{escape(widget)}" data-filled="true"><h3>{escape(chart["title"])}</h3>{svg}</div>'


def _render_simple_bar_svg(series: list[dict[str, Any]]) -> str:
    width = 760
    height = 260
    max_value = max(max(float(item["value"]), 1.0) for item in series)
    bar_width = 70
    gap = 24
    x = 60
    bars = []
    labels = []
    for item in series:
        value = float(item["value"])
        bar_height = (value / max_value) * 160
        y = 210 - bar_height
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="14" fill="#0c7abf" opacity="0.9"></rect>')
        labels.append(f'<text x="{x + bar_width/2:.1f}" y="230" text-anchor="middle" font-size="12" fill="#5f7283">{escape(str(item["label"]))}</text>')
        labels.append(f'<text x="{x + bar_width/2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" fill="#12263a">{value:.0f}</text>')
        x += bar_width + gap
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="260" role="img">{"".join(bars)}{"".join(labels)}</svg>'


def _render_financial_svg(series: list[dict[str, Any]]) -> str:
    width = 760
    height = 290
    max_value = max(max(float(item["investment"]), float(item["value"]), 1.0) for item in series)
    scale = 170 / max_value
    bars = []
    points = []
    labels = []
    x = 70
    for item in series:
        investment = float(item["investment"])
        value = float(item["value"])
        investment_h = investment * scale
        value_y = 220 - (value * scale)
        bars.append(f'<rect x="{x}" y="{220 - investment_h:.1f}" width="42" height="{investment_h:.1f}" rx="10" fill="#b7d7ea"></rect>')
        points.append(f"{x + 72},{value_y:.1f}")
        labels.append(f'<text x="{x + 20}" y="246" font-size="12" fill="#5f7283">{escape(item["label"])}</text>')
        x += 120
    polyline = f'<polyline fill="none" stroke="#0b8f63" stroke-width="4" points="{" ".join(points)}"></polyline>'
    circles = "".join(
        f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="5" fill="#0b8f63"></circle>'
        for point in points
    )
    legend = (
        '<text x="42" y="24" font-size="12" fill="#5f7283">Investment</text>'
        '<rect x="18" y="13" width="16" height="10" rx="3" fill="#b7d7ea"></rect>'
        '<text x="150" y="24" font-size="12" fill="#5f7283">Business Value</text>'
        '<line x1="118" y1="18" x2="142" y2="18" stroke="#0b8f63" stroke-width="4"></line>'
    )
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="290" role="img">{legend}{"".join(bars)}{polyline}{circles}{"".join(labels)}</svg>'


def _render_matrix(matrix: dict[str, Any] | None) -> str:
    if not matrix:
        return ""
    columns = []
    for name, items in matrix["items"].items():
        item_list = "".join(f"<li>{escape(item)}</li>" for item in items)
        columns.append(f'<div class="matrix-column"><h4>{escape(name)}</h4><ul>{item_list}</ul></div>')
    return f'<div class="matrix" data-widget="{escape(matrix["widget"])}" data-filled="true">{"".join(columns)}</div>'


def _render_timeline(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    rendered = []
    for item in items:
        rendered.append(
            '<div class="timeline-item">'
            f'<div><div class="timeline-year">{escape(item["year"])}</div><div class="timeline-meta">{escape(item["phase"])}</div></div>'
            f'<div><strong>{escape(item["milestone"])}</strong><div class="timeline-meta">Investment {escape(item["investment"])} | Business Value {escape(item["business_value"])}</div></div>'
            "</div>"
        )
    return f'<div class="timeline" data-widget="roadmap-timeline" data-filled="true">{"".join(rendered)}</div>'


def _render_delivery_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    rendered = []
    for card in cards:
        waves = "".join(f"<li>{escape(item)}</li>" for item in card["wave_ownership"])
        rendered.append(
            '<div class="delivery-card">'
            f'<div class="title">{escape(card["title"])}</div>'
            f'<div>{escape(card["subtitle"])}</div>'
            f'<div class="share">{escape(str(card["fte_share_pct"]))}%</div>'
            f'<div>{escape(card["primary_scope"])}</div>'
            f'<div><strong>Governance:</strong> {escape(card["governance_owner_role"])}</div>'
            f'<div><strong>Wave ownership</strong><ul>{waves}</ul></div>'
            "</div>"
        )
    return f'<div class="delivery-grid" data-widget="delivery-layout" data-filled="true">{"".join(rendered)}</div>'


def _render_fact_refs(fact_refs: list[str], facts: dict[str, Any]) -> str:
    if not fact_refs:
        return ""
    rows = []
    for key in fact_refs:
        value = facts.get(key)
        if isinstance(value, float):
            if key.endswith("_pct") or key == "roi_pct":
                rendered = f"{value:.2f}%"
            else:
                rendered = format_currency(value)
        else:
            rendered = escape(str(value))
        rows.append(f"<tr><th>{escape(key)}</th><td>{escape(str(rendered))}</td></tr>")
    return f'<div class="panel"><h3>Fact Traceability</h3><table><tbody>{"".join(rows)}</tbody></table></div>'
