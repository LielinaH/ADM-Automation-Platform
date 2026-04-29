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
    nav = _render_sidebar(client, facts)
    masthead = _render_masthead(client, facts)
    screens = "\n".join(_render_screen(sections[section.identifier], facts, client) for section in SECTIONS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <style>
    :root {{
      --nav-bg: #0b1621;
      --nav-panel: #0f1e2d;
      --nav-text: #e5edf5;
      --nav-muted: #8da4bb;
      --page-bg: #edf2f7;
      --surface: #ffffff;
      --surface-alt: #f6fafc;
      --surface-ink: #14283a;
      --muted: #5f7283;
      --border: #dbe4eb;
      --line: #edf2f6;
      --cyan: #00bceb;
      --cyan-deep: #00779b;
      --teal: #0f8f74;
      --mint: #4dc7ae;
      --ink: #0f2234;
      --shadow-xl: 0 36px 80px rgba(12, 34, 52, 0.12);
      --shadow-lg: 0 18px 42px rgba(12, 34, 52, 0.08);
      --radius-xl: 28px;
      --radius-2xl: 42px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Aptos", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(0,188,235,0.10), transparent 32%),
        radial-gradient(circle at bottom left, rgba(15,143,116,0.08), transparent 28%),
        linear-gradient(180deg, #f7fafc 0%, #edf2f7 100%);
    }}
    a {{ color: inherit; }}
    .shell {{
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      background:
        radial-gradient(circle at top left, rgba(0,188,235,0.18), transparent 24%),
        linear-gradient(180deg, var(--nav-panel) 0%, var(--nav-bg) 100%);
      color: var(--nav-text);
      border-right: 1px solid rgba(255,255,255,0.07);
      display: flex;
      flex-direction: column;
    }}
    .brand-block {{
      padding: 28px 28px 24px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      background: rgba(2,8,14,0.24);
    }}
    .brand-row {{
      display: flex;
      gap: 16px;
      align-items: center;
    }}
    .brand-mark {{
      width: 58px;
      height: 58px;
      border-radius: 18px;
      background: linear-gradient(135deg, var(--cyan) 0%, #62d4f4 100%);
      color: white;
      display: grid;
      place-items: center;
      box-shadow: 0 12px 32px rgba(0,188,235,0.28);
      flex: none;
    }}
    .brand-mark svg {{
      width: 30px;
      height: 30px;
    }}
    .brand-title {{
      margin: 0;
      font-size: 28px;
      line-height: 1.04;
      letter-spacing: -0.04em;
      font-weight: 900;
    }}
    .brand-subtitle {{
      margin: 6px 0 0;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.42em;
      color: rgba(229,237,245,0.62);
      font-weight: 800;
    }}
    .brand-meta {{
      margin-top: 18px;
      display: grid;
      gap: 8px;
      color: var(--nav-muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .brand-metrics {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .brand-kpi {{
      padding: 12px 12px 13px;
      border-radius: 16px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.07);
    }}
    .brand-kpi .label {{
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: rgba(229,237,245,0.55);
      margin-bottom: 6px;
    }}
    .brand-kpi .value {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.04em;
      color: white;
    }}
    .nav-scroll {{
      padding: 24px 0 12px;
      flex: 1;
    }}
    .nav-group {{
      margin-bottom: 22px;
    }}
    .nav-group-title {{
      padding: 0 28px;
      margin-bottom: 10px;
      font-size: 10px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.34em;
      color: rgba(229,237,245,0.46);
    }}
    .nav-link {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 28px;
      border-left: 4px solid transparent;
      text-decoration: none;
      color: var(--nav-muted);
      font-size: 14px;
      font-weight: 700;
      transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
    }}
    .nav-link:hover {{
      background: rgba(255,255,255,0.045);
      color: white;
    }}
    .nav-link.active {{
      background: linear-gradient(90deg, rgba(0,188,235,0.24), rgba(0,188,235,0.05));
      color: white;
      border-left-color: var(--cyan);
    }}
    .nav-index {{
      width: 26px;
      height: 26px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      font-size: 12px;
      font-weight: 900;
      background: rgba(255,255,255,0.08);
      color: rgba(229,237,245,0.9);
      flex: none;
    }}
    .nav-link.active .nav-index {{
      background: var(--cyan);
      color: #08212f;
    }}
    .sidebar-footer {{
      padding: 20px 28px 28px;
      border-top: 1px solid rgba(255,255,255,0.08);
      display: grid;
      gap: 12px;
    }}
    .print-button {{
      appearance: none;
      border: none;
      border-radius: 16px;
      padding: 14px 16px;
      background: linear-gradient(135deg, var(--cyan) 0%, #54d8f6 100%);
      color: #092132;
      font-size: 14px;
      font-weight: 900;
      letter-spacing: 0.01em;
      cursor: pointer;
      box-shadow: 0 16px 38px rgba(0,188,235,0.22);
    }}
    .footer-caption {{
      color: rgba(229,237,245,0.58);
      font-size: 11px;
      line-height: 1.5;
    }}
    .workspace {{
      min-width: 0;
      padding: 26px 28px 34px;
      display: grid;
      gap: 18px;
    }}
    .masthead {{
      position: relative;
      overflow: hidden;
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
      gap: 20px;
      padding: 26px 28px;
      border-radius: 34px;
      background:
        radial-gradient(circle at top right, rgba(0,188,235,0.16), transparent 26%),
        radial-gradient(circle at bottom left, rgba(15,143,116,0.11), transparent 24%),
        linear-gradient(135deg, #fdfefe 0%, #f2f8fb 100%);
      border: 1px solid rgba(219,228,235,0.94);
      box-shadow: var(--shadow-lg);
    }}
    .masthead::after {{
      content: "";
      position: absolute;
      right: -50px;
      top: -70px;
      width: 230px;
      height: 230px;
      border-radius: 44px;
      transform: rotate(-14deg);
      background: linear-gradient(135deg, rgba(0,188,235,0.08), rgba(15,143,116,0.05));
      pointer-events: none;
    }}
    .masthead-copy,
    .masthead-stats {{
      position: relative;
      z-index: 1;
    }}
    .masthead-label {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(0,188,235,0.10);
      color: var(--cyan-deep);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .masthead-label::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--cyan);
      box-shadow: 0 0 0 5px rgba(0,188,235,0.12);
    }}
    .masthead-title {{
      margin: 18px 0 10px;
      font-size: 56px;
      line-height: 0.92;
      letter-spacing: -0.06em;
      font-weight: 950;
      text-transform: uppercase;
      font-style: italic;
      color: var(--surface-ink);
      max-width: 760px;
    }}
    .masthead-copy p {{
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.68;
      font-weight: 600;
    }}
    .masthead-meta {{
      margin-top: 20px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .masthead-meta span {{
      padding: 9px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.86);
      border: 1px solid rgba(219,228,235,0.94);
      color: #4e6578;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      box-shadow: 0 8px 22px rgba(12, 34, 52, 0.05);
    }}
    .masthead-stats {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .masthead-stat {{
      padding: 18px 18px 20px;
      border-radius: 24px;
      background: rgba(255,255,255,0.90);
      border: 1px solid rgba(219,228,235,0.94);
      box-shadow: 0 12px 30px rgba(12, 34, 52, 0.06);
    }}
    .masthead-stat .label {{
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #73889b;
      margin-bottom: 10px;
    }}
    .masthead-stat .value {{
      font-size: 32px;
      line-height: 1.0;
      font-weight: 950;
      letter-spacing: -0.05em;
      color: var(--surface-ink);
    }}
    .masthead-stat .detail {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
      font-weight: 600;
    }}
    .workspace-frame {{
      background: linear-gradient(180deg, rgba(255,255,255,0.56), rgba(255,255,255,0.28));
      border: 1px solid rgba(219,228,235,0.92);
      border-radius: 46px;
      box-shadow: var(--shadow-xl);
      min-height: calc(100vh - 72px);
      position: relative;
      padding: 24px;
    }}
    .screen {{
      display: block;
      padding: 54px 58px 58px;
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(219,228,235,0.92);
      border-radius: 38px;
      box-shadow: var(--shadow-lg);
      margin-bottom: 22px;
      background:
        radial-gradient(circle at top right, rgba(0,188,235,0.10), transparent 24%),
        radial-gradient(circle at bottom left, rgba(15,143,116,0.08), transparent 20%),
        linear-gradient(180deg, rgba(255,255,255,0.82), rgba(245,249,252,0.96));
    }}
    .screen.active {{
      border-color: rgba(0,188,235,0.30);
      box-shadow: 0 22px 56px rgba(12, 34, 52, 0.12);
    }}
    .screen::before {{
      content: "";
      position: absolute;
      top: 28px;
      right: 32px;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      border: 1px dashed rgba(0,119,155,0.12);
      opacity: 0.8;
      pointer-events: none;
    }}
    .screen::after {{
      content: "";
      position: absolute;
      top: 56px;
      right: 58px;
      width: 160px;
      height: 160px;
      border-radius: 36px;
      background: linear-gradient(135deg, rgba(0,188,235,0.08), rgba(15,143,116,0.05));
      transform: rotate(-12deg);
      pointer-events: none;
    }}
    .screen-head {{
      position: relative;
      z-index: 1;
      margin-bottom: 34px;
      padding-bottom: 26px;
      border-bottom: 2px solid rgba(15,34,52,0.06);
    }}
    .screen-meta-strip {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 14px;
    }}
    .screen-index {{
      width: 54px;
      height: 54px;
      border-radius: 18px;
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, var(--surface-ink) 0%, #1e3d55 100%);
      color: white;
      font-size: 18px;
      font-weight: 950;
      letter-spacing: -0.04em;
      box-shadow: 0 16px 34px rgba(20, 40, 58, 0.22);
    }}
    .screen-tag {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(0,188,235,0.08);
      color: var(--cyan-deep);
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.16em;
    }}
    .screen-tag .dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--cyan);
      box-shadow: 0 0 0 5px rgba(0,188,235,0.12);
    }}
    .screen-title {{
      margin: 18px 0 10px;
      font-size: 54px;
      line-height: 0.96;
      letter-spacing: -0.06em;
      font-weight: 950;
      text-transform: uppercase;
      color: var(--surface-ink);
      max-width: 820px;
      font-style: italic;
    }}
    .screen-summary {{
      margin: 0;
      max-width: 920px;
      font-size: 19px;
      line-height: 1.65;
      color: var(--muted);
      font-weight: 600;
    }}
    .content-stack {{
      position: relative;
      z-index: 1;
      display: grid;
      gap: 26px;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.9fr);
      gap: 22px;
      align-items: start;
    }}
    .statement-card,
    .section-block,
    .data-card,
    .trace-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 30px;
      box-shadow: var(--shadow-lg);
    }}
    .statement-card {{
      padding: 30px;
      display: grid;
      gap: 22px;
    }}
    .statement-card.cover-aside {{
      background:
        radial-gradient(circle at top right, rgba(0,188,235,0.10), transparent 24%),
        linear-gradient(180deg, #ffffff 0%, #f6fafc 100%);
    }}
    .statement-card h3,
    .section-block h3,
    .data-card h3,
    .trace-card h3 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: -0.03em;
      color: var(--surface-ink);
    }}
    .section-block,
    .data-card,
    .trace-card {{
      padding: 26px;
    }}
    .narrative {{
      display: grid;
      gap: 14px;
    }}
    .narrative p {{
      margin: 0;
      font-size: 16px;
      line-height: 1.72;
      color: #274153;
    }}
    .summary-callouts {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    .summary-callout {{
      display: flex;
      gap: 14px;
      align-items: start;
      padding: 14px 16px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(0,188,235,0.06), rgba(0,188,235,0.02));
      border: 1px solid rgba(0,188,235,0.12);
      color: #1f4459;
      font-weight: 600;
      line-height: 1.55;
      min-height: 100%;
      box-shadow: 0 10px 24px rgba(12, 34, 52, 0.05);
    }}
    .summary-callout .bullet {{
      margin-top: 7px;
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--cyan);
      flex: none;
    }}
    .metric-board,
    .value-board,
    .target-board,
    .signal-board {{
      display: grid;
      gap: 18px;
    }}
    .metric-grid,
    .target-grid,
    .signal-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .metric-card,
    .target-card,
    .signal-card {{
      background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px;
      display: grid;
      gap: 12px;
      box-shadow: 0 10px 24px rgba(12, 34, 52, 0.05);
    }}
    .metric-top,
    .target-top,
    .signal-top {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 12px;
    }}
    .metric-name,
    .target-name,
    .signal-name {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.03em;
      color: var(--surface-ink);
    }}
    .metric-scope,
    .target-detail,
    .signal-segment {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      line-height: 1.45;
    }}
    .metric-delta,
    .target-value {{
      padding: 7px 11px;
      border-radius: 999px;
      background: rgba(0,188,235,0.09);
      color: var(--cyan-deep);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .metric-scale {{
      height: 10px;
      border-radius: 999px;
      background: #ebf2f6;
      overflow: hidden;
      border: 1px solid rgba(219,228,235,0.92);
    }}
    .metric-scale-fill,
    .value-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--cyan), var(--mint));
    }}
    .metric-values {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: #324d60;
      font-size: 13px;
      font-weight: 700;
    }}
    .metric-values span:last-child {{
      color: var(--teal);
    }}
    .value-board-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
      gap: 16px;
    }}
    .value-mix {{
      display: grid;
      gap: 12px;
    }}
    .value-row {{
      display: grid;
      gap: 8px;
      padding: 14px 16px;
      border-radius: 20px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbfc 100%);
      border: 1px solid var(--border);
    }}
    .value-row-top {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
    }}
    .value-row-top .name {{
      font-size: 14px;
      font-weight: 900;
      letter-spacing: 0.02em;
      color: var(--surface-ink);
      text-transform: uppercase;
    }}
    .value-row-top .amount {{
      font-size: 20px;
      font-weight: 950;
      letter-spacing: -0.04em;
      color: var(--cyan-deep);
    }}
    .value-track {{
      height: 10px;
      border-radius: 999px;
      background: #ebf2f6;
      overflow: hidden;
      border: 1px solid rgba(219,228,235,0.92);
    }}
    .year-strip {{
      display: grid;
      gap: 10px;
    }}
    .year-chip {{
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
      display: grid;
      gap: 4px;
    }}
    .year-chip .year {{
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #708496;
    }}
    .year-chip .net {{
      font-size: 20px;
      font-weight: 950;
      letter-spacing: -0.04em;
      color: var(--surface-ink);
    }}
    .year-chip .state {{
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .year-chip.positive .net,
    .year-chip.positive .state {{
      color: var(--teal);
    }}
    .year-chip.negative .net,
    .year-chip.negative .state {{
      color: #b5475b;
    }}
    .signal-metric-list {{
      display: grid;
      gap: 9px;
    }}
    .signal-metric {{
      padding: 10px 12px;
      border-radius: 16px;
      background: var(--surface-alt);
      border: 1px solid var(--border);
    }}
    .signal-metric .label {{
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #708496;
      margin-bottom: 6px;
    }}
    .signal-metric .value {{
      font-size: 13px;
      font-weight: 700;
      color: #294559;
      line-height: 1.55;
    }}
    .kpi-band {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }}
    .kpi-card {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(180deg, #ffffff 0%, #f5fafc 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px 18px 20px;
      min-height: 132px;
    }}
    .kpi-card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 5px;
      background: linear-gradient(90deg, var(--cyan), var(--mint));
      opacity: 0.95;
    }}
    .kpi-card .label {{
      font-size: 11px;
      line-height: 1.4;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #6b8093;
      margin-bottom: 10px;
    }}
    .kpi-card .value {{
      font-size: 34px;
      line-height: 1.0;
      letter-spacing: -0.06em;
      font-weight: 950;
      color: var(--surface-ink);
      margin-bottom: 8px;
    }}
    .kpi-card .subtitle {{
      font-size: 13px;
      line-height: 1.55;
      color: var(--muted);
      font-weight: 600;
    }}
    .insight-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .insight-card {{
      background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 20px;
      display: grid;
      gap: 10px;
    }}
    .benchmark-card {{
      position: relative;
      overflow: hidden;
      padding-top: 24px;
    }}
    .benchmark-card::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 6px;
      background: linear-gradient(90deg, var(--cyan), var(--mint));
    }}
    .benchmark-chip {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(0,188,235,0.08);
      color: var(--cyan-deep);
      font-size: 10px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.14em;
    }}
    .insight-card .title {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.03em;
      color: var(--surface-ink);
    }}
    .insight-card .metric {{
      font-size: 30px;
      line-height: 1.0;
      letter-spacing: -0.05em;
      font-weight: 950;
      color: var(--cyan-deep);
    }}
    .insight-card .detail {{
      color: var(--muted);
      font-weight: 600;
      line-height: 1.6;
    }}
    .insight-card strong,
    .delivery-card strong,
    .matrix-column strong {{
      color: var(--surface-ink);
      font-size: 11px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    .insight-card ul,
    .delivery-card ul,
    .matrix-column ul {{
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }}
    .insight-card li,
    .delivery-card li,
    .matrix-column li {{
      position: relative;
      padding-left: 16px;
      color: #30495b;
      line-height: 1.55;
      font-weight: 600;
    }}
    .insight-card li::before,
    .delivery-card li::before,
    .matrix-column li::before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0.62em;
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--cyan), var(--mint));
      box-shadow: 0 0 0 4px rgba(0,188,235,0.08);
    }}
    .table-card {{
      overflow: hidden;
      padding: 0;
    }}
    .table-title {{
      padding: 24px 26px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }}
    .table-title p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }}
    .table-scroll {{
      overflow-x: auto;
      border-top: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
      font-size: 14px;
    }}
    thead {{
      background: linear-gradient(180deg, #f7fafc 0%, #eef4f8 100%);
    }}
    th {{
      padding: 14px 16px;
      text-align: left;
      font-size: 11px;
      letter-spacing: 0.14em;
      font-weight: 900;
      text-transform: uppercase;
      color: #6b8093;
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
    }}
    td {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      color: #254052;
      line-height: 1.55;
    }}
    tbody tr:nth-child(even) {{
      background: rgba(246,250,252,0.68);
    }}
    .viz-shell {{
      padding: 26px;
    }}
    .viz-head {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 20px;
    }}
    .viz-head p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      font-weight: 600;
      max-width: 540px;
    }}
    .svg-shell {{
      background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 18px;
    }}
    .matrix-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 14px;
    }}
    .matrix-column {{
      background: linear-gradient(180deg, #ffffff 0%, #f5f9fb 100%);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 18px;
      min-height: 220px;
      position: relative;
      overflow: hidden;
    }}
    .matrix-column::before {{
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 6px;
      background: linear-gradient(90deg, var(--cyan), var(--mint));
      opacity: 0.85;
    }}
    .matrix-column h4 {{
      margin: 6px 0 12px;
      font-size: 15px;
      letter-spacing: -0.02em;
      text-transform: uppercase;
      font-weight: 900;
      color: var(--surface-ink);
    }}
    .matrix-column ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 9px;
      color: #2b4659;
      line-height: 1.5;
      font-size: 14px;
    }}
    .timeline-flow {{
      position: relative;
      margin-left: 18px;
      padding-left: 48px;
      display: grid;
      gap: 28px;
      border-left: 8px solid #eef4f8;
    }}
    .timeline-item {{
      position: relative;
      background: linear-gradient(180deg, #ffffff 0%, #f7fbfd 100%);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 24px 24px 22px;
      box-shadow: var(--shadow-lg);
    }}
    .timeline-item::before {{
      content: "";
      position: absolute;
      left: -61px;
      top: 26px;
      width: 22px;
      height: 22px;
      border-radius: 999px;
      background: var(--cyan);
      border: 6px solid white;
      box-shadow: 0 10px 22px rgba(0,188,235,0.24);
    }}
    .timeline-top {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      align-items: center;
      margin-bottom: 14px;
    }}
    .timeline-year {{
      font-size: 34px;
      line-height: 1.0;
      font-weight: 950;
      letter-spacing: -0.05em;
      color: var(--surface-ink);
    }}
    .timeline-phase {{
      padding: 8px 14px;
      border-radius: 999px;
      background: #edf6fb;
      color: var(--cyan-deep);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.15em;
      text-transform: uppercase;
    }}
    .timeline-meta {{
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #6b8093;
    }}
    .timeline-body {{
      font-size: 18px;
      line-height: 1.7;
      color: #314d60;
      font-weight: 600;
      max-width: 860px;
    }}
    .delivery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
    }}
    .delivery-card {{
      background: linear-gradient(180deg, #ffffff 0%, #f8fbfc 100%);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 22px;
      box-shadow: var(--shadow-lg);
      display: grid;
      gap: 12px;
    }}
    .delivery-top {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 16px;
    }}
    .delivery-place {{
      font-size: 21px;
      font-weight: 900;
      letter-spacing: -0.03em;
      color: var(--surface-ink);
    }}
    .delivery-type {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.14em;
    }}
    .delivery-share {{
      font-size: 34px;
      line-height: 1.0;
      font-weight: 950;
      color: var(--teal);
      letter-spacing: -0.05em;
      white-space: nowrap;
    }}
    .delivery-card ul {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
      color: #305062;
      line-height: 1.5;
      font-size: 14px;
    }}
    .delivery-strip {{
      display: flex;
      height: 16px;
      border-radius: 999px;
      overflow: hidden;
      background: #edf3f7;
      border: 1px solid var(--border);
    }}
    .delivery-strip span {{
      height: 100%;
    }}
    .trace-card details {{
      display: grid;
      gap: 16px;
    }}
    .trace-card summary {{
      cursor: pointer;
      font-weight: 900;
      color: var(--surface-ink);
      list-style: none;
    }}
    .trace-card summary::-webkit-details-marker {{
      display: none;
    }}
    .trace-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .trace-card summary {{
      cursor: pointer;
      list-style: none;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--cyan-deep);
      margin-bottom: 16px;
    }}
    .trace-card summary::-webkit-details-marker {{
      display: none;
    }}
    .trace-item {{
      padding: 14px 16px;
      border-radius: 18px;
      background: var(--surface-alt);
      border: 1px solid var(--border);
      min-height: 92px;
    }}
    .trace-item .key {{
      font-size: 10px;
      line-height: 1.5;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #6b8093;
      margin-bottom: 8px;
    }}
    .trace-item .value {{
      font-size: 14px;
      line-height: 1.55;
      color: #294559;
      font-weight: 700;
      word-break: break-word;
    }}
    .cover-visual {{
      position: relative;
      overflow: hidden;
      border-radius: 26px;
      border: 1px solid var(--border);
      background:
        radial-gradient(circle at top left, rgba(0,188,235,0.16), transparent 24%),
        linear-gradient(135deg, #113049 0%, #0f2234 54%, #0d1824 100%);
      min-height: 230px;
      padding: 22px;
      color: white;
      box-shadow: 0 18px 46px rgba(11, 22, 33, 0.24);
    }}
    .cover-visual::after {{
      content: "";
      position: absolute;
      right: -44px;
      top: -56px;
      width: 180px;
      height: 180px;
      border-radius: 36px;
      transform: rotate(-18deg);
      background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.03));
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .cover-visual-top {{
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
    }}
    .cover-badge {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.08);
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .cover-logo {{
      width: 56px;
      height: 56px;
      border-radius: 18px;
      display: grid;
      place-items: center;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.10);
    }}
    .cover-visual h3 {{
      margin: 0 0 10px;
      font-size: 28px;
      line-height: 1.0;
      letter-spacing: -0.04em;
      color: white;
    }}
    .cover-visual p {{
      margin: 0;
      max-width: 420px;
      color: rgba(229,237,245,0.82);
      font-size: 14px;
      line-height: 1.65;
      font-weight: 600;
    }}
    .cover-stat-ribbon {{
      position: relative;
      z-index: 1;
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .cover-stat {{
      padding: 12px 12px 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.10);
    }}
    .cover-stat .label {{
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(229,237,245,0.62);
      margin-bottom: 6px;
    }}
    .cover-stat .value {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.04em;
      color: white;
    }}
    .cover-kpis {{
      display: grid;
      gap: 16px;
    }}
    .cover-mini {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .cover-mini .mini {{
      padding: 14px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: var(--surface-alt);
    }}
    .cover-mini .mini .label {{
      font-size: 10px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: #708496;
      margin-bottom: 6px;
    }}
    .cover-mini .mini .value {{
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -0.04em;
      color: var(--surface-ink);
    }}
    .footer-note {{
      margin-top: 4px;
      text-align: center;
      color: #728799;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .hide-screen {{
      display: none;
    }}
    @media (max-width: 1320px) {{
      .masthead {{ grid-template-columns: 1fr; }}
      .hero-grid {{ grid-template-columns: 1fr; }}
      .value-board-grid {{ grid-template-columns: 1fr; }}
      .matrix-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    }}
    @media (max-width: 1120px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: relative; height: auto; }}
      .workspace {{ padding: 18px; }}
      .workspace-frame {{ min-height: auto; }}
      .masthead-title {{ font-size: 42px; }}
      .screen {{ padding: 28px 22px 30px; }}
      .screen-title {{ font-size: 40px; }}
      .matrix-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 780px) {{
      .brand-metrics,
      .cover-mini,
      .cover-stat-ribbon {{
        grid-template-columns: 1fr;
      }}
      .screen-title {{
        font-size: 32px;
      }}
      .matrix-grid {{
        grid-template-columns: 1fr;
      }}
      .timeline-flow {{
        margin-left: 0;
        padding-left: 28px;
      }}
      .timeline-item::before {{
        left: -41px;
      }}
    }}
    @media print {{
      body {{ background: white; }}
      .shell {{ display: block; }}
      .sidebar {{ display: none; }}
      .workspace {{ padding: 0; }}
      .workspace-frame {{
        border: none;
        box-shadow: none;
        border-radius: 0;
        padding: 0;
      }}
      .masthead {{
        page-break-after: avoid;
        box-shadow: none;
      }}
      .screen {{
        break-inside: avoid;
        page-break-inside: avoid;
        padding: 22px 0 30px;
        background: white;
        border: none;
        box-shadow: none;
        margin-bottom: 12px;
      }}
      .screen::before,
      .screen::after {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    {nav}
    <main class="workspace">
      <div class="workspace-frame">
        {masthead}
        {screens}
      </div>
      <div class="footer-note">Transformation blueprint · financial case · delivery roadmap</div>
    </main>
  </div>
  <script>
    (function() {{
      var sections = Array.prototype.slice.call(document.querySelectorAll('.screen'));
      var links = Array.prototype.slice.call(document.querySelectorAll('.nav-link'));
      function activate(id) {{
        var resolved = id || (sections[0] && sections[0].id);
        links.forEach(function(link) {{
          link.classList.toggle('active', link.getAttribute('href') === '#' + resolved);
        }});
        sections.forEach(function(section) {{
          section.classList.toggle('active', section.id === resolved);
        }});
      }}
      links.forEach(function(link) {{
        link.addEventListener('click', function() {{
          var targetId = this.getAttribute('href').slice(1);
          activate(targetId);
        }});
      }});
      if ('IntersectionObserver' in window) {{
        var observer = new IntersectionObserver(function(entries) {{
          entries.forEach(function(entry) {{
            if (entry.isIntersecting) {{
              activate(entry.target.id);
            }}
          }});
        }}, {{
          rootMargin: '-22% 0px -54% 0px',
          threshold: [0.2, 0.45, 0.7]
        }});
        sections.forEach(function(section) {{
          observer.observe(section);
        }});
      }}
      window.addEventListener('hashchange', function() {{
        activate(window.location.hash.slice(1));
      }});
      activate(window.location.hash.slice(1));
    }})();
  </script>
</body>
</html>"""


def _render_sidebar(client: dict[str, Any], facts: dict[str, Any]) -> str:
    groups: dict[str, list[str]] = {}
    for index, section in enumerate(SECTIONS, start=1):
        groups.setdefault(section.nav_group, []).append(
            f'<a class="nav-link{" active" if index == 1 else ""}" href="#{section.identifier}"><span class="nav-index">{index:02d}</span><span>{escape(section.title)}</span></a>'
        )
    group_html = "".join(
        f'<div class="nav-group"><div class="nav-group-title">{escape(group_name)}</div>{"".join(links)}</div>'
        for group_name, links in groups.items()
    )
    initials = _company_initials(client["company"]["name"])
    return (
        '<aside class="sidebar">'
        '<div class="brand-block">'
        '<div class="brand-row">'
        f'<div class="brand-mark" aria-hidden="true">{_render_mark_svg(initials)}</div>'
        '<div>'
        f'<h1 class="brand-title">{escape(client["company"]["name"])}</h1>'
        '<p class="brand-subtitle">Transformation Master Plan</p>'
        '</div>'
        '</div>'
        f'<div class="brand-meta"><div>{escape(client["company"]["industry"])} · {escape(client["company"].get("subsector", ""))}</div><div>{escape(client["company"]["headquarters"])}</div></div>'
        '<div class="brand-metrics">'
        f'<div class="brand-kpi"><div class="label">Annual ADM</div><div class="value">{escape(format_currency(facts["annual_adm_spend_usd"]))}</div></div>'
        f'<div class="brand-kpi"><div class="label">Target ROI</div><div class="value">{escape(f"{facts["roi_pct"]:.2f}%")}</div></div>'
        f'<div class="brand-kpi"><div class="label">Apps</div><div class="value">{facts["apps_in_scope"]}</div></div>'
        f'<div class="brand-kpi"><div class="label">Value</div><div class="value">{escape(format_currency(facts["cumulative_business_value_usd"]))}</div></div>'
        '</div>'
        '</div>'
        f'<div class="nav-scroll">{group_html}</div>'
        '<div class="sidebar-footer">'
        '<button class="print-button" type="button" data-action="print-report" onclick="window.print()">Export / Print</button>'
        '<div class="footer-caption">Choose a section from the left rail. Print mode expands every screen for publication output.</div>'
        '</div>'
        '</aside>'
    )


def _render_masthead(client: dict[str, Any], facts: dict[str, Any]) -> str:
    company = client["company"]
    return (
        '<section class="masthead" aria-label="Report cover summary">'
        '<div class="masthead-copy">'
        '<div class="masthead-label">Account Development Master</div>'
        f'<h1 class="masthead-title">{escape(company["name"])} transformation blueprint</h1>'
        f'<p>This ADM condenses the client estate into an executive narrative, transformation roadmap, financial case, and delivery blueprint aligned to the benchmark report style.</p>'
        '<div class="masthead-meta">'
        f'<span>{escape(company["industry"])}</span>'
        f'<span>{escape(company.get("subsector", "Enterprise Transformation"))}</span>'
        f'<span>{escape(company["headquarters"])}</span>'
        f'<span>{facts["apps_in_scope"]} apps in scope</span>'
        '</div>'
        '</div>'
        '<div class="masthead-stats">'
        f'<div class="masthead-stat"><div class="label">Five-Year Contract Value</div><div class="value">{escape(format_currency(facts["tcv_5y_usd"]))}</div><div class="detail">Computed from the locked ADM spend baseline across the full program horizon.</div></div>'
        f'<div class="masthead-stat"><div class="label">Transformation Investment</div><div class="value">{escape(format_currency(facts["transformation_investment_total_usd"]))}</div><div class="detail">Code-derived investment curve applied across the five-year transformation horizon.</div></div>'
        f'<div class="masthead-stat"><div class="label">Modeled Business Value</div><div class="value">{escape(format_currency(facts["cumulative_business_value_usd"]))}</div><div class="detail">Workforce, legacy, productivity, and resilience value streams combined into one benchmark-ready value story.</div></div>'
        '</div>'
        '</section>'
    )


def _render_screen(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    body = _render_screen_body(section, facts, client)
    active_class = " active" if section["section_id"] == SECTIONS[0].identifier else ""
    section_number = _section_number(section["section_id"])
    return (
        f'<section id="{escape(section["section_id"])}" class="screen{active_class}" data-section-id="{escape(section["section_id"])}">'
        f'<div class="screen-head"><div class="screen-meta-strip"><div class="screen-index">{section_number:02d}</div><div class="screen-tag"><span class="dot"></span>{escape(section["phase"])}</div></div><h2 class="screen-title">{escape(section["title"])}</h2><p class="screen-summary">{escape(section["summary"])}</p></div>'
        f'<div class="content-stack">{body}</div>'
        '</section>'
    )


def _render_screen_body(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    section_id = section["section_id"]
    if section_id == "sec01":
        return _render_executive_screen(section, facts, client)
    if section_id == "sec02":
        return _render_portfolio_screen(section, facts)
    if section_id == "sec03":
        return _render_inventory_screen(section, facts)
    if section_id == "sec04":
        return _render_benchmark_screen(section, facts, client)
    if section_id == "sec05":
        return _render_strategy_screen(section, facts)
    if section_id == "sec06":
        return _render_factory_screen(section, facts)
    if section_id == "sec07":
        return _render_cloud_data_screen(section, facts)
    if section_id == "sec08":
        return _render_financial_screen(section, facts, client)
    if section_id == "sec09":
        return _render_roadmap_screen(section, facts)
    if section_id == "sec10":
        return _render_delivery_screen(section, facts)
    if section_id == "sec11":
        return _render_summary_screen(section, facts, client)
    if section_id == "sec12":
        return _render_partnership_screen(section, facts)
    return _render_generic_screen(section, facts)


def _render_executive_screen(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    metrics = client.get("narrative_context", {}).get("current_state_metrics", [])
    return (
        '<div class="hero-grid">'
        f'<div class="statement-card" data-widget="hero-callout" data-filled="true"><h3>Transformation Thesis</h3>{_render_narrative(section.get("narrative", []))}{_render_summary_callouts(section.get("callouts", []))}</div>'
        '<div class="statement-card cover-aside">'
        f'{_render_kpi_band(section.get("kpi_cards", []), "kpi-grid")}'
        f'{_render_cover_visual(client, facts)}'
        '<div class="cover-mini">'
        f'<div class="mini"><div class="label">Enterprise Revenue</div><div class="value">{escape(format_currency(float(client["company"]["annual_revenue_usd"])))}</div></div>'
        f'<div class="mini"><div class="label">Employees</div><div class="value">{client["company"]["employees"]:,}</div></div>'
        f'<div class="mini"><div class="label">App Estate</div><div class="value">{facts["apps_in_scope"]} apps</div></div>'
        f'<div class="mini"><div class="label">Delivery Centers</div><div class="value">{facts["delivery_center_count"]}</div></div>'
        '</div>'
        '</div>'
        '</div>'
        f'{_render_metric_progress_board(metrics, "Current-State Performance Reset", "executive-metrics")}'
        f'{_render_visual_block("Estate Transformation Posture", "Application density, dependency load, and delivery-mix reset anchored to the locked client ingress.", _render_estate_snapshot_svg(facts, client), "executive-estate-visual")}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_portfolio_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_kpi_band(section.get("kpi_cards", []), "portfolio-kpis")}'
        f'{_render_section_block("Portfolio Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Portfolio Signals", section.get("callouts", []))}'
        f'{_render_insight_cards(section.get("cards", []), "portfolio-cards")}'
        f'{_render_visual_block("Portfolio Distribution by Business Unit", "Cost and application count concentration across the estate.", _render_chart(section.get("chart")), "portfolio-chart")}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_inventory_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_kpi_band(section.get("kpi_cards", []), "inventory-kpis")}'
        f'{_render_section_block("Inventory Framing", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Disposition Takeaways", section.get("callouts", []))}'
        f'{_render_tables(section.get("tables", []))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_benchmark_screen(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Benchmark Positioning", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Gap-Closing Imperatives", section.get("callouts", []))}'
        f'{_render_benchmark_cards(section.get("cards", []), "competitor-cards")}'
        f'{_render_competitor_signal_board(client.get("competitors", []))}'
        f'{_render_visual_block("Gap Closure Index", "Normalized gap-closure view across the client’s highest-signal performance metrics.", _render_benchmark_gap_svg(client.get("narrative_context", {}).get("current_state_metrics", [])), "benchmark-gap-visual")}'
        f'{_render_tables(section.get("tables", []))}'
        + _render_traceability(section.get("evidence_refs", []), None, title="Evidence Markers")
    )


def _render_strategy_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Strategic Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Priority AI Plays", section.get("callouts", []))}'
        f'{_render_insight_cards(section.get("cards", []), "transformation-pillars")}'
        + _render_traceability(section.get("evidence_refs", []), None, title="Evidence Markers")
    )


def _render_factory_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_kpi_band(section.get("kpi_cards", []), "factory-kpis")}'
        f'{_render_section_block("Factory Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Factory Implications", section.get("callouts", []))}'
        f'{_render_matrix(section.get("matrix"))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_cloud_data_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Cloud & Data Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_kpi_band(section.get("kpi_cards", []), "cloud-data-kpis")}'
        f'{_render_signal_block("Architecture Implications", section.get("callouts", []))}'
        f'{_render_insight_cards(section.get("cards", []), "cloud-data-cards")}'
        f'{_render_tables(section.get("tables", []))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_financial_screen(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Financial Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_kpi_band(section.get("kpi_cards", []), "financial-kpis")}'
        f'{_render_signal_block("Value Interpretation", section.get("callouts", []))}'
        f'{_render_value_stream_board(facts)}'
        f'{_render_visual_block("Value Bridge", "Waterfall view from transformation investment through the modeled value streams to net value creation.", _render_value_bridge_svg(facts), "financial-value-bridge")}'
        f'{_render_tables(section.get("tables", []))}'
        f'{_render_visual_block("5-Year Investment vs Value", "Five-year view of investment phasing against modeled business value realization.", _render_chart(section.get("chart")), "financial-chart")}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_roadmap_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Roadmap Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Program Guardrails", section.get("callouts", []))}'
        f'{_render_timeline(section.get("timeline", []))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_delivery_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    strip = _render_delivery_strip(section.get("delivery_cards", []))
    return (
        f'{_render_kpi_band(section.get("kpi_cards", []), "delivery-kpis")}'
        f'{_render_section_block("Delivery Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Operating Model Principles", section.get("callouts", []))}'
        f'<div class="section-block"><h3>Delivery Footprint Allocation</h3>{strip}</div>'
        f'{_render_delivery_cards(section.get("delivery_cards", []))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_summary_screen(section: dict[str, Any], facts: dict[str, Any], client: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Executive Synthesis", _render_narrative(section.get("narrative", [])))}'
        f'{_render_signal_block("Board-Level Takeaways", section.get("callouts", []))}'
        f'{_render_target_board(client.get("targets", {}), facts)}'
        f'{_render_visual_block("Target Outcome Mix", "Closing section view of the target-state operating outcomes tied back to the financial anchor.", _render_target_outcome_svg(client.get("targets", {}), facts), "target-outcome-visual")}'
        f'{_render_insight_cards(section.get("cards", []), "benchmark-summary")}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_partnership_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_kpi_band(section.get("kpi_cards", []), "partnership-kpis")}'
        f'{_render_section_block("Operating Model Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_insight_cards(section.get("cards", []), "partnership-overview")}'
        f'{_render_section_block("Execution Assumptions", _render_summary_callouts(section.get("callouts", [])))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_generic_screen(section: dict[str, Any], facts: dict[str, Any]) -> str:
    return (
        f'{_render_section_block("Narrative", _render_narrative(section.get("narrative", [])))}'
        f'{_render_kpi_band(section.get("kpi_cards", []), "kpi-grid")}'
        f'{_render_insight_cards(section.get("cards", []), "cards")}'
        f'{_render_tables(section.get("tables", []))}'
        + _render_traceability(section.get("fact_refs", []), facts)
    )


def _render_section_block(title: str, inner: str) -> str:
    if not inner:
        return ""
    return f'<div class="section-block"><h3>{escape(title)}</h3>{inner}</div>'


def _render_narrative(paragraphs: list[str]) -> str:
    if not paragraphs:
        return ""
    return '<div class="narrative">' + "".join(f"<p>{escape(text)}</p>" for text in paragraphs) + "</div>"


def _render_summary_callouts(callouts: list[str]) -> str:
    if not callouts:
        return ""
    return '<div class="summary-callouts">' + "".join(
        f'<div class="summary-callout"><span class="bullet"></span><span>{escape(item)}</span></div>' for item in callouts
    ) + "</div>"


def _render_signal_block(title: str, callouts: list[str]) -> str:
    return _render_section_block(title, _render_summary_callouts(callouts))


def _render_metric_progress_board(metrics: list[dict[str, Any]], title: str, widget: str) -> str:
    if not metrics:
        return ""
    cards = []
    for metric in metrics:
        baseline = float(metric.get("baseline_value", 0) or 0)
        target = float(metric.get("target_value", 0) or 0)
        unit = str(metric.get("baseline_unit") or metric.get("target_unit") or "")
        improvement = _metric_delta_label(baseline, target, unit)
        gap_width = _metric_gap_width(baseline, target)
        cards.append(
            '<div class="metric-card">'
            '<div class="metric-top">'
            f'<div><div class="metric-name">{escape(str(metric.get("name", "Metric")))}</div><div class="metric-scope">{escape(str(metric.get("scope", "Enterprise")))}</div></div>'
            f'<div class="metric-delta">{escape(improvement)}</div>'
            '</div>'
            f'<div class="metric-scale"><div class="metric-scale-fill" style="width:{gap_width:.0f}%;"></div></div>'
            f'<div class="metric-values"><span>Baseline {_format_metric_value(metric.get("baseline_value"), unit)}</span><span>Target {_format_metric_value(metric.get("target_value"), unit)}</span></div>'
            '</div>'
        )
    inner = f'<div class="metric-board"><div class="metric-grid">{"".join(cards)}</div></div>'
    return f'<div class="data-card" data-widget="{escape(widget)}" data-filled="true"><h3>{escape(title)}</h3>{inner}</div>'


def _render_competitor_signal_board(competitors: list[dict[str, Any]]) -> str:
    if not competitors:
        return ""
    cards = []
    for competitor in competitors:
        metrics = competitor.get("competitor_metrics", [])[:2]
        metric_html = "".join(
            '<div class="signal-metric">'
            f'<div class="label">{escape(_humanize_metric_name(str(metric.get("metric_name", "Signal"))))} · {escape(str(metric.get("metric_year", "")))}</div>'
            f'<div class="value">{escape(str(metric.get("metric_value", "")))}</div>'
            '</div>'
            for metric in metrics
        )
        signals = competitor.get("evidence_signals", [])[:2]
        signal_points = "".join(f"<li>{escape(item)}</li>" for item in signals)
        cards.append(
            '<div class="signal-card">'
            '<div class="signal-top">'
            f'<div><div class="signal-name">{escape(str(competitor.get("name", "Competitor")))}</div><div class="signal-segment">{escape(str(competitor.get("segment", "")))}</div></div>'
            f'<div class="benchmark-chip">{escape(str(metrics[0].get("confidence", "Medium") if metrics else "Medium"))} confidence</div>'
            '</div>'
            f'<div class="signal-metric-list">{metric_html}</div>'
            f'<div><strong>Signals</strong><ul>{signal_points}</ul></div>'
            '</div>'
        )
    return f'<div class="data-card" data-widget="competitor-signal-board" data-filled="true"><h3>Competitor Signal Snapshot</h3><div class="signal-board"><div class="signal-grid">{"".join(cards)}</div></div></div>'


def _render_value_stream_board(facts: dict[str, Any]) -> str:
    streams = [
        ("Workforce savings", float(facts.get("workforce_savings_rate_arbitrage_cumulative_usd", 0) or 0)),
        ("Legacy cost reduction", float(facts.get("legacy_cost_reduction_cumulative_usd", 0) or 0)),
        ("Productivity value", float(facts.get("productivity_value_cumulative_usd", 0) or 0)),
        ("Resilience value", float(facts.get("resilience_value_cumulative_usd", 0) or 0)),
    ]
    if not any(amount for _, amount in streams):
        return ""
    max_amount = max(amount for _, amount in streams) or 1.0
    mix = []
    for name, amount in streams:
        width = max(10.0, (amount / max_amount) * 100.0)
        mix.append(
            '<div class="value-row">'
            f'<div class="value-row-top"><div class="name">{escape(name)}</div><div class="amount">{escape(format_currency(amount))}</div></div>'
            f'<div class="value-track"><div class="value-fill" style="width:{width:.0f}%;"></div></div>'
            '</div>'
        )
    year_chips = []
    for index, amount in enumerate(facts.get("yearly_investment_net_usd", []), start=1):
        amount_float = float(amount or 0)
        chip_class = "positive" if amount_float >= 0 else "negative"
        state = "Net positive" if amount_float >= 0 else "Investment-led"
        year_chips.append(
            f'<div class="year-chip {chip_class}">'
            f'<div class="year">Year {index}</div>'
            f'<div class="net">{escape(format_currency(amount_float))}</div>'
            f'<div class="state">{escape(state)}</div>'
            '</div>'
        )
    inner = (
        '<div class="value-board">'
        '<div class="value-board-grid">'
        f'<div class="value-mix">{"".join(mix)}</div>'
        f'<div class="year-strip">{"".join(year_chips)}</div>'
        '</div>'
        '</div>'
    )
    return f'<div class="data-card" data-widget="financial-value-board" data-filled="true"><h3>Value Stream Profile</h3>{inner}</div>'


def _render_target_board(targets: dict[str, Any], facts: dict[str, Any]) -> str:
    if not targets:
        return ""
    roi_label = f'{float(facts["roi_pct"]):.2f}%'
    net_value_label = format_currency(float(facts["net_value_created_usd"]))
    total_value_label = format_currency(float(facts["cumulative_business_value_usd"]))
    ordered_targets = [
        ("Cloud migration", targets.get("cloud_migration_pct"), "workloads shifted into the target-state cloud footprint"),
        ("Legacy reduction", targets.get("legacy_cost_reduction_pct"), "run-cost removed from the legacy estate"),
        ("Release uplift", targets.get("release_frequency_improvement_pct"), "release-velocity improvement against the current baseline"),
        ("Failure-rate reduction", targets.get("change_failure_rate_reduction_pct"), "stability gain from platform and delivery modernization"),
        ("Innovation shift", targets.get("innovation_budget_shift_pct"), "budget rebalanced from maintenance into innovation"),
    ]
    cards = []
    for label, value, detail in ordered_targets:
        if value is None:
            continue
        cards.append(
            '<div class="target-card">'
            '<div class="target-top">'
            f'<div><div class="target-name">{escape(label)}</div><div class="target-detail">{escape(detail)}</div></div>'
            f'<div class="target-value">{escape(f"{float(value):.0f}%")}</div>'
            '</div>'
            f'<div class="metric-scale"><div class="metric-scale-fill" style="width:{max(8.0, min(float(value), 100.0)):.0f}%;"></div></div>'
            '</div>'
        )
    anchor = (
        f'<div class="summary-callouts">'
        f'<div class="summary-callout"><span class="bullet"></span><span>Modeled ROI anchor: {escape(roi_label)} from {escape(net_value_label)} net value created.</span></div>'
        f'<div class="summary-callout"><span class="bullet"></span><span>Five-year value pool: {escape(total_value_label)} supported by workforce, legacy, productivity, and resilience value streams.</span></div>'
        '</div>'
    )
    return f'<div class="data-card" data-widget="target-board" data-filled="true"><h3>Target-State Outcome Board</h3><div class="target-board"><div class="target-grid">{"".join(cards)}</div>{anchor}</div></div>'


def _render_kpi_band(cards: list[dict[str, Any]], widget: str) -> str:
    if not cards:
        return ""
    items = []
    for card in cards:
        items.append(
            '<div class="kpi-card">'
            f'<div class="label">{escape(card["label"])}</div>'
            f'<div class="value">{escape(card["value"])}</div>'
            f'<div class="subtitle">{escape(card["subtitle"])}</div>'
            '</div>'
        )
    return f'<div class="kpi-band" data-widget="{escape(widget)}" data-filled="true">{"".join(items)}</div>'


def _render_insight_cards(cards: list[dict[str, Any]], widget: str) -> str:
    if not cards:
        return ""
    rendered = []
    for card in cards:
        title = card.get("title") or ""
        metric = card.get("metric") or card.get("value") or ""
        detail = card.get("detail") or card.get("subtitle") or ""
        lists = []
        if card.get("strengths"):
            lists.append("<strong>Public strengths</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["strengths"]) + "</ul>")
        if card.get("gaps"):
            lists.append("<strong>Client gap</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["gaps"]) + "</ul>")
        if card.get("signals"):
            lists.append("<strong>Signals</strong><ul>" + "".join(f"<li>{escape(item)}</li>" for item in card["signals"]) + "</ul>")
        rendered.append(
            '<div class="insight-card">'
            f'<div class="title">{escape(str(title))}</div>'
            + (f'<div class="metric">{escape(str(metric))}</div>' if metric else "")
            + (f'<div class="detail">{escape(str(detail))}</div>' if detail else "")
            + "".join(lists)
            + '</div>'
        )
    return f'<div class="insight-grid" data-widget="{escape(widget)}" data-filled="true">{"".join(rendered)}</div>'


def _render_benchmark_cards(cards: list[dict[str, Any]], widget: str) -> str:
    if not cards:
        return ""
    rendered = []
    for card in cards:
        strengths = "".join(f"<li>{escape(item)}</li>" for item in card.get("strengths", []))
        gaps = "".join(f"<li>{escape(item)}</li>" for item in card.get("gaps", []))
        signals = "".join(f"<li>{escape(item)}</li>" for item in card.get("signals", []))
        rendered.append(
            '<div class="insight-card benchmark-card">'
            f'<div class="benchmark-chip">{escape(str(card.get("segment", "")))}</div>'
            f'<div class="title">{escape(str(card.get("title", "")))}</div>'
            f'<div><strong>Public strengths</strong><ul>{strengths}</ul></div>'
            f'<div><strong>Client gap</strong><ul>{gaps}</ul></div>'
            f'<div><strong>Signals</strong><ul>{signals}</ul></div>'
            '</div>'
        )
    return f'<div class="insight-grid" data-widget="{escape(widget)}" data-filled="true">{"".join(rendered)}</div>'


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
            f'<div class="data-card table-card"{widget_attr}>'
            f'<div class="table-title"><div><h3>{escape(table["title"])}</h3><p>{len(table["rows"])} rows</p></div></div>'
            f'<div class="table-scroll"><table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></div>'
            '</div>'
        )
    return "".join(rendered)


def _render_visual_block(title: str, caption: str, inner: str, widget: str) -> str:
    if not inner:
        return ""
    return (
        f'<div class="data-card viz-shell" data-widget="{escape(widget)}" data-filled="true">'
        f'<div class="viz-head"><div><h3>{escape(title)}</h3></div><p>{escape(caption)}</p></div>'
        f'{inner}'
        '</div>'
    )


def _render_chart(chart: dict[str, Any] | None) -> str:
    if not chart:
        return ""
    widget = chart.get("widget", "chart")
    if widget == "financial-chart":
        svg = _render_financial_svg(chart["series"])
    else:
        svg = _render_simple_bar_svg(chart["series"])
    return f'<div class="svg-shell">{svg}</div>'


def _render_estate_snapshot_svg(facts: dict[str, Any], client: dict[str, Any]) -> str:
    width = 920
    height = 360
    stats = [
        ("Apps", str(facts["apps_in_scope"])),
        ("Avg Age", f'{float(facts["average_app_age_years"]):.1f}y'),
        ("Dependencies", str(facts["dependency_edges"])),
        ("Run-Cost Ratio", f'{float(facts["run_cost_to_adm_ratio"]) * 100:.1f}%'),
    ]
    stat_blocks = []
    positions = [(32, 34), (242, 34), (32, 132), (242, 132)]
    for (label, value), (x, y) in zip(stats, positions):
        stat_blocks.append(
            f'<g><rect x="{x}" y="{y}" width="178" height="76" rx="18" fill="#f7fbfd" stroke="#dbe4eb"></rect>'
            f'<text x="{x + 18}" y="{y + 24}" font-size="11" font-weight="900" letter-spacing="1.6" fill="#708496">{escape(label.upper())}</text>'
            f'<text x="{x + 18}" y="{y + 56}" font-size="28" font-weight="950" fill="#14283a">{escape(value)}</text></g>'
        )
    bu_mix = sorted(facts.get("run_cost_by_business_unit_usd", {}).items(), key=lambda item: float(item[1]), reverse=True)
    max_cost = max((float(value) for _, value in bu_mix), default=1.0)
    bu_bars = []
    base_x = 462
    base_y = 66
    for index, (name, value) in enumerate(bu_mix):
        y = base_y + index * 40
        bar_width = (float(value) / max_cost) * 250.0
        bu_bars.append(
            f'<g><text x="{base_x}" y="{y}" font-size="12" font-weight="800" fill="#5f7283">{escape(name)}</text>'
            f'<rect x="{base_x}" y="{y + 10}" width="250" height="12" rx="6" fill="#eaf2f6"></rect>'
            f'<rect x="{base_x}" y="{y + 10}" width="{bar_width:.1f}" height="12" rx="6" fill="#00bceb"></rect>'
            f'<text x="{base_x + 262}" y="{y + 21}" font-size="12" font-weight="900" fill="#14283a">{escape(_format_currency_short(float(value)))}</text></g>'
        )
    delivery = client.get("financial_assumptions", {})
    current_mix = delivery.get("current_delivery_mix_pct", {})
    target_mix = delivery.get("target_delivery_mix_pct", {})
    mix_colors = {"onshore": "#073b5a", "nearshore": "#4dc7ae", "offshore": "#00bceb"}
    current_segments = _render_mix_bar_svg(42, 254, 300, 16, current_mix, mix_colors)
    target_segments = _render_mix_bar_svg(42, 304, 300, 16, target_mix, mix_colors)
    legend = []
    for idx, key in enumerate(("onshore", "nearshore", "offshore")):
        x = 462 + idx * 120
        legend.append(
            f'<g><rect x="{x}" y="286" width="12" height="12" rx="6" fill="{mix_colors[key]}"></rect>'
            f'<text x="{x + 18}" y="296" font-size="12" font-weight="800" fill="#5f7283">{escape(key.title())}</text></g>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="360" role="img">'
        '<rect x="12" y="12" width="896" height="336" rx="28" fill="#ffffff" stroke="#dbe4eb"></rect>'
        '<text x="32" y="26" font-size="10" font-weight="900" letter-spacing="2.2" fill="#00779b">ESTATE SNAPSHOT</text>'
        f'{"".join(stat_blocks)}'
        '<text x="462" y="34" font-size="14" font-weight="900" fill="#14283a">Run-cost concentration by business unit</text>'
        f'{"".join(bu_bars)}'
        '<text x="42" y="238" font-size="14" font-weight="900" fill="#14283a">Delivery mix reset</text>'
        '<text x="42" y="250" font-size="11" font-weight="800" fill="#708496">Current</text>'
        '<text x="42" y="300" font-size="11" font-weight="800" fill="#708496">Target</text>'
        f'{current_segments}{target_segments}'
        f'{"".join(legend)}'
        '</svg>'
    )


def _render_benchmark_gap_svg(metrics: list[dict[str, Any]]) -> str:
    if not metrics:
        return ""
    width = 920
    height = 360
    rows = []
    max_gap = max((_metric_gap_width(float(m.get("baseline_value", 0) or 0), float(m.get("target_value", 0) or 0)) for m in metrics), default=100.0)
    for index, metric in enumerate(metrics[:4]):
        y = 52 + index * 72
        baseline = float(metric.get("baseline_value", 0) or 0)
        target = float(metric.get("target_value", 0) or 0)
        unit = str(metric.get("baseline_unit") or metric.get("target_unit") or "")
        gap = _metric_gap_width(baseline, target)
        width_fill = (gap / max_gap) * 330.0 if max_gap else 80.0
        delta = _metric_delta_label(baseline, target, unit)
        rows.append(
            f'<g><text x="32" y="{y}" font-size="13" font-weight="900" fill="#14283a">{escape(str(metric.get("name", "Metric")))}</text>'
            f'<text x="32" y="{y + 18}" font-size="11" font-weight="800" fill="#708496">{escape(str(metric.get("scope", "Enterprise")))}</text>'
            f'<text x="470" y="{y}" font-size="11" font-weight="900" fill="#00779b">{escape(delta.upper())}</text>'
            f'<rect x="470" y="{y + 10}" width="330" height="12" rx="6" fill="#eaf2f6"></rect>'
            f'<rect x="470" y="{y + 10}" width="{width_fill:.1f}" height="12" rx="6" fill="#00bceb"></rect>'
            f'<text x="32" y="{y + 46}" font-size="12" font-weight="700" fill="#324d60">Baseline {_format_metric_value(baseline, unit)}</text>'
            f'<text x="260" y="{y + 46}" font-size="12" font-weight="700" fill="#0f8f74">Target {_format_metric_value(target, unit)}</text></g>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="360" role="img">'
        '<rect x="12" y="12" width="896" height="336" rx="28" fill="#ffffff" stroke="#dbe4eb"></rect>'
        '<text x="32" y="28" font-size="10" font-weight="900" letter-spacing="2.2" fill="#00779b">BENCHMARK GAP</text>'
        '<text x="470" y="28" font-size="11" font-weight="900" fill="#708496">Normalized gap-closure requirement</text>'
        f'{"".join(rows)}'
        '</svg>'
    )


def _render_value_bridge_svg(facts: dict[str, Any]) -> str:
    width = 920
    height = 360
    deltas = [
        ("Investment", -float(facts.get("transformation_investment_total_usd", 0) or 0), "#d7edf7"),
        ("Workforce", float(facts.get("workforce_savings_rate_arbitrage_cumulative_usd", 0) or 0), "#00bceb"),
        ("Legacy", float(facts.get("legacy_cost_reduction_cumulative_usd", 0) or 0), "#0f8f74"),
        ("Productivity", float(facts.get("productivity_value_cumulative_usd", 0) or 0), "#4dc7ae"),
        ("Resilience", float(facts.get("resilience_value_cumulative_usd", 0) or 0), "#8fdcc8"),
    ]
    cumulative = 0.0
    min_value = 0.0
    max_value = 0.0
    for _, amount, _ in deltas:
        cumulative += amount
        min_value = min(min_value, cumulative, amount, 0.0)
        max_value = max(max_value, cumulative, amount, 0.0)
    final_total = float(facts.get("net_value_created_usd", 0) or 0)
    min_value = min(min_value, final_total)
    max_value = max(max_value, final_total)
    span = max(abs(min_value), abs(max_value), 1.0)
    scale = 130.0 / span
    zero_y = 210.0
    x = 58.0
    bar_width = 92.0
    gap = 36.0
    pieces = ['<line x1="40" y1="210" x2="880" y2="210" stroke="#dbe4eb" stroke-width="2"></line>']
    running = 0.0
    prev_end_x = None
    prev_y = zero_y
    for label, amount, color in deltas:
        next_running = running + amount
        start_y = zero_y - (running * scale)
        end_y = zero_y - (next_running * scale)
        top = min(start_y, end_y)
        height_bar = abs(end_y - start_y) or 1.0
        pieces.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bar_width:.1f}" height="{height_bar:.1f}" rx="16" fill="{color}"></rect>')
        if prev_end_x is not None:
            pieces.append(f'<line x1="{prev_end_x:.1f}" y1="{prev_y:.1f}" x2="{x:.1f}" y2="{start_y:.1f}" stroke="#94a8b8" stroke-dasharray="4 4"></line>')
        pieces.append(f'<text x="{x + bar_width / 2:.1f}" y="{top - 10:.1f}" text-anchor="middle" font-size="12" font-weight="900" fill="#14283a">{escape(_format_currency_short(amount))}</text>')
        pieces.append(f'<text x="{x + bar_width / 2:.1f}" y="244" text-anchor="middle" font-size="12" font-weight="900" fill="#6b8093">{escape(label)}</text>')
        running = next_running
        prev_end_x = x + bar_width
        prev_y = end_y
        x += bar_width + gap
    final_y = zero_y - (final_total * scale)
    top = min(zero_y, final_y)
    height_bar = abs(final_y - zero_y) or 1.0
    pieces.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bar_width:.1f}" height="{height_bar:.1f}" rx="16" fill="#14283a"></rect>')
    pieces.append(f'<text x="{x + bar_width / 2:.1f}" y="{top - 10:.1f}" text-anchor="middle" font-size="12" font-weight="900" fill="#14283a">{escape(_format_currency_short(final_total))}</text>')
    pieces.append(f'<text x="{x + bar_width / 2:.1f}" y="244" text-anchor="middle" font-size="12" font-weight="900" fill="#6b8093">Net Value</text>')
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="360" role="img">'
        '<rect x="12" y="12" width="896" height="336" rx="28" fill="#ffffff" stroke="#dbe4eb"></rect>'
        '<text x="32" y="28" font-size="10" font-weight="900" letter-spacing="2.2" fill="#00779b">VALUE BRIDGE</text>'
        '<text x="32" y="332" font-size="11" font-weight="800" fill="#708496">Bridge from transformation investment to net value created</text>'
        f'{"".join(pieces)}'
        '</svg>'
    )


def _render_target_outcome_svg(targets: dict[str, Any], facts: dict[str, Any]) -> str:
    if not targets:
        return ""
    width = 920
    height = 360
    items = [
        ("Cloud", float(targets.get("cloud_migration_pct", 0) or 0), "#00bceb"),
        ("Legacy", float(targets.get("legacy_cost_reduction_pct", 0) or 0), "#0f8f74"),
        ("Release", float(targets.get("release_frequency_improvement_pct", 0) or 0), "#4dc7ae"),
        ("Failure", float(targets.get("change_failure_rate_reduction_pct", 0) or 0), "#8fdcc8"),
        ("Innovation", float(targets.get("innovation_budget_shift_pct", 0) or 0), "#073b5a"),
    ]
    bars = []
    for index, (label, value, color) in enumerate(items):
        y = 54 + index * 52
        bars.append(
            f'<g><text x="32" y="{y}" font-size="13" font-weight="900" fill="#14283a">{escape(label)}</text>'
            f'<rect x="136" y="{y - 10}" width="360" height="14" rx="7" fill="#eaf2f6"></rect>'
            f'<rect x="136" y="{y - 10}" width="{(max(6.0, min(value, 100.0)) * 3.6):.1f}" height="14" rx="7" fill="{color}"></rect>'
            f'<text x="510" y="{y + 1}" font-size="12" font-weight="900" fill="#14283a">{value:.0f}%</text></g>'
        )
    roi = float(facts.get("roi_pct", 0) or 0)
    total_value = float(facts.get("cumulative_business_value_usd", 0) or 0)
    net_value = float(facts.get("net_value_created_usd", 0) or 0)
    cards = (
        f'<rect x="610" y="52" width="260" height="96" rx="20" fill="#f7fbfd" stroke="#dbe4eb"></rect>'
        f'<text x="632" y="78" font-size="11" font-weight="900" letter-spacing="1.6" fill="#708496">ROI ANCHOR</text>'
        f'<text x="632" y="120" font-size="34" font-weight="950" fill="#14283a">{roi:.2f}%</text>'
        f'<rect x="610" y="172" width="260" height="120" rx="20" fill="#f7fbfd" stroke="#dbe4eb"></rect>'
        f'<text x="632" y="198" font-size="11" font-weight="900" letter-spacing="1.6" fill="#708496">VALUE CREATED</text>'
        f'<text x="632" y="234" font-size="26" font-weight="950" fill="#14283a">{escape(_format_currency_short(total_value))}</text>'
        f'<text x="632" y="264" font-size="12" font-weight="800" fill="#5f7283">Net after investment: {escape(_format_currency_short(net_value))}</text>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="360" role="img">'
        '<rect x="12" y="12" width="896" height="336" rx="28" fill="#ffffff" stroke="#dbe4eb"></rect>'
        '<text x="32" y="28" font-size="10" font-weight="900" letter-spacing="2.2" fill="#00779b">TARGET OUTCOMES</text>'
        f'{"".join(bars)}{cards}'
        '</svg>'
    )


def _render_mix_bar_svg(x: float, y: float, width: float, height: float, mix: dict[str, Any], colors: dict[str, str]) -> str:
    segments = []
    cursor = x
    for key in ("onshore", "nearshore", "offshore"):
        share = float(mix.get(key, 0) or 0)
        segment_width = width * (share / 100.0)
        if segment_width <= 0:
            continue
        segments.append(f'<rect x="{cursor:.1f}" y="{y:.1f}" width="{segment_width:.1f}" height="{height:.1f}" rx="{height/2:.1f}" fill="{colors[key]}"></rect>')
        segments.append(f'<text x="{cursor + segment_width / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="11" font-weight="900" fill="#5f7283">{share:.0f}%</text>')
        cursor += segment_width
    segments.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="{height/2:.1f}" fill="none" stroke="#dbe4eb"></rect>')
    return "".join(segments)


def _render_simple_bar_svg(series: list[dict[str, Any]]) -> str:
    width = 900
    height = 340
    base_y = 266
    max_value = max(max(float(item["value"]), 1.0) for item in series)
    bar_width = 90
    gap = 42
    x = 82
    bars = []
    labels = []
    for item in series:
        value = float(item["value"])
        bar_height = (value / max_value) * 170
        y = base_y - bar_height
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="18" fill="#00bceb"></rect>')
        labels.append(f'<text x="{x + bar_width/2:.1f}" y="{base_y + 28}" text-anchor="middle" font-size="12" font-weight="800" fill="#6b8093">{escape(str(item["label"]))}</text>')
        labels.append(f'<text x="{x + bar_width/2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-size="13" font-weight="900" fill="#12263a">{value:.0f}</text>')
        x += bar_width + gap
    grid = "".join(f'<line x1="64" y1="{y}" x2="840" y2="{y}" stroke="#edf2f6" stroke-width="1"></line>' for y in (266, 210, 154, 98, 42))
    axis = '<line x1="64" y1="266" x2="840" y2="266" stroke="#d8e2ea" stroke-width="2"></line>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="340" role="img">{grid}{axis}{"".join(bars)}{"".join(labels)}</svg>'


def _render_financial_svg(series: list[dict[str, Any]]) -> str:
    width = 920
    height = 380
    base_y = 286
    max_value = max(max(float(item["investment"]), float(item["value"]), 1.0) for item in series)
    scale = 196 / max_value
    bars = []
    value_points = []
    labels = []
    x = 92
    for item in series:
        investment = float(item["investment"])
        value = float(item["value"])
        investment_h = investment * scale
        investment_y = base_y - investment_h
        value_y = base_y - (value * scale)
        bars.append(f'<rect x="{x}" y="{investment_y:.1f}" width="56" height="{investment_h:.1f}" rx="14" fill="#d7edf7"></rect>')
        value_points.append(f"{x + 90},{value_y:.1f}")
        labels.append(f'<text x="{x + 28}" y="{base_y + 28}" text-anchor="middle" font-size="12" font-weight="900" fill="#6b8093">{escape(item["label"])}</text>')
        x += 142
    polyline = f'<polyline fill="none" stroke="#0f8f74" stroke-width="5" points="{" ".join(value_points)}"></polyline>'
    circles = "".join(
        f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="6" fill="#0f8f74" stroke="white" stroke-width="3"></circle>'
        for point in value_points
    )
    grid = "".join(f'<line x1="74" y1="{y}" x2="864" y2="{y}" stroke="#edf2f6" stroke-width="1"></line>' for y in (286, 236, 186, 136, 86, 36))
    legend = (
        '<g>'
        '<rect x="22" y="18" width="18" height="10" rx="3" fill="#d7edf7"></rect>'
        '<text x="48" y="27" font-size="12" font-weight="900" fill="#6b8093">Investment</text>'
        '<line x1="160" y1="23" x2="184" y2="23" stroke="#0f8f74" stroke-width="5"></line>'
        '<text x="192" y="27" font-size="12" font-weight="900" fill="#6b8093">Business Value</text>'
        '</g>'
    )
    axis = '<line x1="74" y1="286" x2="864" y2="286" stroke="#d8e2ea" stroke-width="2"></line>'
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="380" role="img">{legend}{grid}{axis}{"".join(bars)}{polyline}{circles}{"".join(labels)}</svg>'


def _render_matrix(matrix: dict[str, Any] | None) -> str:
    if not matrix:
        return ""
    columns = []
    for name, items in matrix["items"].items():
        item_list = "".join(f"<li>{escape(item)}</li>" for item in items)
        columns.append(f'<div class="matrix-column"><h4>{escape(name)}</h4><ul>{item_list}</ul></div>')
    return f'<div class="data-card" data-widget="{escape(matrix["widget"])}" data-filled="true"><h3>Modernization Matrix</h3><div class="matrix-grid">{"".join(columns)}</div></div>'


def _render_timeline(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    rendered = []
    for item in items:
        rendered.append(
            '<div class="timeline-item">'
            f'<div class="timeline-top"><div class="timeline-year">{escape(item["year"])}</div><div class="timeline-phase">{escape(item["phase"])}</div><div class="timeline-meta">Investment {escape(item["investment"])} · Business Value {escape(item["business_value"])}</div></div>'
            f'<div class="timeline-body">{escape(item["milestone"])}</div>'
            '</div>'
        )
    return f'<div class="data-card" data-widget="roadmap-timeline" data-filled="true"><h3>Execution Sequence</h3><div class="timeline-flow">{"".join(rendered)}</div></div>'


def _render_delivery_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    rendered = []
    for card in cards:
        waves = "".join(f"<li>{escape(item)}</li>" for item in card["wave_ownership"])
        rendered.append(
            '<div class="delivery-card">'
            '<div class="delivery-top">'
            f'<div><div class="delivery-place">{escape(card["title"])}</div><div class="delivery-type">{escape(card["subtitle"])}</div></div>'
            f'<div class="delivery-share">{escape(str(card["fte_share_pct"]))}%</div>'
            '</div>'
            f'<div>{escape(card["primary_scope"])}</div>'
            f'<div><strong>Governance:</strong> {escape(card["governance_owner_role"])}</div>'
            f'<div><strong>Wave ownership</strong><ul>{waves}</ul></div>'
            '</div>'
        )
    return f'<div class="delivery-grid" data-widget="delivery-layout" data-filled="true">{"".join(rendered)}</div>'


def _render_delivery_strip(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    colors = ["#00bceb", "#0f8f74", "#073b5a", "#8fdcc8"]
    segments = []
    legend = []
    for index, card in enumerate(cards):
        color = colors[index % len(colors)]
        share = float(card["fte_share_pct"])
        segments.append(f'<span style="width:{share}%;background:{color};" title="{escape(card["title"])} {share:.0f}%"></span>')
        legend.append(f'<div style="display:flex;align-items:center;gap:8px;"><span style="width:10px;height:10px;border-radius:999px;background:{color};display:inline-block;"></span><span style="font-size:12px;font-weight:800;color:#5f7283;">{escape(card["title"])} · {share:.0f}%</span></div>')
    return f'<div class="delivery-strip">{"".join(segments)}</div><div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:14px;">{"".join(legend)}</div>'


def _render_traceability(fact_refs: list[str], facts: dict[str, Any] | None, *, title: str = "Data Basis") -> str:
    if not fact_refs:
        return ""
    items = []
    for key in fact_refs:
        value = _format_fact_lookup(key, facts)
        items.append(
            '<div class="trace-item">'
            f'<div class="key">{escape(str(key))}</div>'
            f'<div class="value">{escape(value)}</div>'
            '</div>'
        )
    return (
        '<div class="trace-card">'
        f'<details><summary>{escape(title)}</summary><div class="trace-grid">{"".join(items)}</div></details>'
        '</div>'
    )


def _format_fact_lookup(key: str, facts: dict[str, Any] | None) -> str:
    if facts is None:
      return str(key)
    value = facts.get(key)
    return _format_value(value, key)


def _format_value(value: Any, key: str | None = None) -> str:
    if value is None:
        return "See section packet"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        if key and (key.endswith("_usd") or key.endswith("_revenue") or key.endswith("_investment")):
            return format_currency(float(value))
        return f"{value:,}"
    if isinstance(value, float):
        if key == "run_cost_to_adm_ratio":
            return f"{value * 100:.1f}%"
        if key and (key.endswith("_pct") or key == "roi_pct"):
            return f"{value:.2f}%"
        if key and key.endswith("_usd"):
            return format_currency(value)
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    if isinstance(value, list):
        preview = ", ".join(_format_value(item) for item in value[:5])
        if len(value) > 5:
            preview += ", …"
        return preview
    if isinstance(value, dict):
        parts = [f"{sub_key}: {_format_value(sub_value, sub_key)}" for sub_key, sub_value in list(value.items())[:5]]
        if len(value) > 5:
            parts.append("…")
        return "; ".join(parts)
    return str(value)


def _format_currency_short(value: float) -> str:
    amount = float(value)
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    if absolute >= 1_000_000_000:
        return f"{sign}${absolute / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{sign}${absolute / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{sign}${absolute / 1_000:.1f}K"
    return f"{sign}${absolute:,.0f}"


def _format_metric_value(value: Any, unit: str) -> str:
    if value is None:
        return "N/A"
    unit_map = {
        "days_between_releases": "days",
        "days": "days",
        "hours": "hours",
        "minutes": "min",
        "pct": "%",
        "count": "",
    }
    suffix = unit_map.get(unit, unit.replace("_", " "))
    number = float(value)
    if number.is_integer():
        rendered = f"{int(number):,}"
    else:
        rendered = f"{number:,.1f}"
    if suffix == "%":
        return f"{rendered}%"
    return f"{rendered} {suffix}".strip()


def _metric_delta_label(baseline: float, target: float, unit: str) -> str:
    if baseline <= 0:
        return "Target state"
    if target < baseline and target > 0:
        ratio = baseline / target
        if unit in {"days_between_releases", "hours", "minutes"}:
            return f"{ratio:.1f}x faster"
        delta_pct = ((baseline - target) / baseline) * 100.0
        return f"{delta_pct:.0f}% lower"
    if target > baseline:
        delta_pct = ((target - baseline) / baseline) * 100.0
        return f"{delta_pct:.0f}% lift"
    return "No change"


def _metric_gap_width(baseline: float, target: float) -> float:
    if baseline <= 0:
        return 12.0
    gap = abs(target - baseline) / baseline * 100.0
    return max(12.0, min(gap, 100.0))


def _humanize_metric_name(name: str) -> str:
    return name.replace("_", " ").strip().title()


def _company_initials(name: str) -> str:
    parts = [part[0] for part in name.split() if part and part[0].isalnum()]
    return "".join(parts[:2]).upper() or "AD"


def _section_number(section_id: str) -> int:
    for index, section in enumerate(SECTIONS, start=1):
        if section.identifier == section_id:
            return index
    return 0


def _render_cover_visual(client: dict[str, Any], facts: dict[str, Any]) -> str:
    initials = _company_initials(client["company"]["name"])
    offshore_target = client["financial_assumptions"]["target_delivery_mix_pct"]["offshore"]
    return (
        '<div class="cover-visual">'
        '<div class="cover-visual-top">'
        '<div class="cover-badge">Transformation outlook</div>'
        f'<div class="cover-logo" aria-hidden="true">{_render_mark_svg(initials)}</div>'
        '</div>'
        f'<h3>{escape(client["company"]["name"])} operating transformation</h3>'
        '<p>A modern operating model anchored in estate simplification, faster execution, and measurable value capture across the transformation horizon.</p>'
        '<div class="cover-stat-ribbon">'
        f'<div class="cover-stat"><div class="label">ADM Base</div><div class="value">{escape(format_currency(facts["annual_adm_spend_usd"]))}</div></div>'
        f'<div class="cover-stat"><div class="label">Estate Age</div><div class="value">{facts["average_app_age_years"]:.1f} yrs</div></div>'
        f'<div class="cover-stat"><div class="label">Delivery Mix</div><div class="value">{offshore_target:.0f}% off</div></div>'
        '</div>'
        '</div>'
    )


def _render_mark_svg(initials: str) -> str:
    return (
        '<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="4" y="4" width="40" height="40" rx="12" fill="rgba(255,255,255,0.18)"></rect>'
        '<path d="M14 32V17h5l5 7 5-7h5v15h-4V23l-6 8-6-8v9h-4Z" fill="white"></path>'
        f'<text x="24" y="43" text-anchor="middle" font-size="6" font-weight="900" fill="white">{escape(initials)}</text>'
        '</svg>'
    )
