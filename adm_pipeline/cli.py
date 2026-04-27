"""CLI entrypoint for the ADM pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adm_pipeline.constants import DEFAULT_MODEL, DEFAULT_PROVIDER, DEFAULT_REASONING_EFFORT, DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT_SECONDS, SCENARIO_MODE_LOCKED
from adm_pipeline.critique import critique_sections, load_generated_sections, run_repair_if_needed
from adm_pipeline.facts import build_section_inputs, compute_facts
from adm_pipeline.generation import generate_sections
from adm_pipeline.html_qa import qa_rendered_html
from adm_pipeline.providers import ProviderConfig
from adm_pipeline.render import render_report
from adm_pipeline.run_state import init_manifest, init_run_layout, load_manifest, save_manifest
from adm_pipeline.utils import ensure_dir, read_json, slugify, utc_now_iso, write_json
from adm_pipeline.validation import validate_client_payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adm", description="ADM pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a client ingress payload")
    validate_parser.add_argument("input_path", type=Path)
    validate_parser.set_defaults(func=cmd_validate)

    calculate_parser = subparsers.add_parser("calculate", help="Validate ingress and compute run facts")
    calculate_parser.add_argument("input_path", type=Path)
    calculate_parser.add_argument("--run-dir", type=Path, default=None)
    add_provider_args(calculate_parser)
    calculate_parser.set_defaults(func=cmd_calculate)

    generate_parser = subparsers.add_parser("generate", help="Generate section payloads")
    generate_parser.add_argument("input_path", type=Path)
    generate_parser.add_argument("--run-dir", type=Path, required=True)
    generate_parser.add_argument("--force", action="store_true")
    add_provider_args(generate_parser)
    generate_parser.set_defaults(func=cmd_generate)

    critique_parser = subparsers.add_parser("critique", help="Critique generated sections and optionally repair them")
    critique_parser.add_argument("--run-dir", type=Path, required=True)
    critique_parser.add_argument("--repair", action="store_true")
    add_provider_args(critique_parser)
    critique_parser.set_defaults(func=cmd_critique)

    render_parser = subparsers.add_parser("render", help="Render the final HTML report")
    render_parser.add_argument("--run-dir", type=Path, required=True)
    render_parser.add_argument("--out", type=Path, default=None)
    render_parser.set_defaults(func=cmd_render)

    qa_parser = subparsers.add_parser("qa-html", help="Run final HTML QA")
    qa_parser.add_argument("--run-dir", type=Path, required=True)
    qa_parser.add_argument("--html-path", type=Path, default=None)
    qa_parser.set_defaults(func=cmd_qa_html)

    run_parser = subparsers.add_parser("run", help="Run the full pipeline end to end")
    run_parser.add_argument("input_path", type=Path)
    run_parser.add_argument("--run-dir", type=Path, default=None)
    run_parser.add_argument("--force", action="store_true")
    add_provider_args(run_parser)
    run_parser.set_defaults(func=cmd_run)
    return parser


def add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, dest="provider_kind")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=2)


def cmd_validate(args: argparse.Namespace) -> int:
    payload = read_json(args.input_path)
    report = validate_client_payload(payload)
    if report.errors:
        print("Validation failed:")
        for error in report.errors:
            print(f"- {error}")
        return 1
    print("Validation passed.")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"- {warning}")
    return 0


def cmd_calculate(args: argparse.Namespace) -> int:
    run_dir = args.run_dir or _default_run_dir(args.input_path)
    payload, report = _load_and_validate(args.input_path)
    if report.errors:
        _print_validation_errors(report)
        return 1
    provider_config = _provider_config_from_args(args)
    _prepare_run(run_dir, args.input_path, payload, provider_config)
    facts = compute_facts(payload)
    section_inputs = build_section_inputs(payload, facts)
    write_json(run_dir / "facts.json", facts)
    for section_id, packet in section_inputs.items():
        write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)
    manifest = load_manifest(run_dir)
    manifest.setdefault("step_status", {})["calculate"] = "pass"
    save_manifest(run_dir, manifest)
    print(f"Calculated facts and section inputs in {run_dir}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    payload, report = _load_and_validate(args.input_path)
    if report.errors:
        _print_validation_errors(report)
        return 1
    provider_config = _provider_config_from_args(args)
    run_dir = args.run_dir
    _prepare_run(run_dir, args.input_path, payload, provider_config)
    facts = _ensure_calculated(run_dir, payload)
    section_inputs = _load_or_build_section_inputs(run_dir, payload, facts)
    generate_sections(run_dir, section_inputs, provider_config, force=args.force)
    manifest = load_manifest(run_dir)
    manifest.setdefault("step_status", {})["generate"] = "pass"
    save_manifest(run_dir, manifest)
    print(f"Generated section payloads in {run_dir}")
    return 0


def cmd_critique(args: argparse.Namespace) -> int:
    run_dir = args.run_dir
    manifest = load_manifest(run_dir)
    payload = read_json(Path(manifest["input_path"]))
    facts = read_json(run_dir / "facts.json")
    sections = load_generated_sections(run_dir)
    report = critique_sections(run_dir, facts, sections)
    if args.repair and report.get("repair_candidates"):
        provider_config = _provider_config_from_args(args)
        section_inputs = _load_or_build_section_inputs(run_dir, payload, facts)
        run_repair_if_needed(run_dir, section_inputs, provider_config, report)
        sections = load_generated_sections(run_dir)
        report = critique_sections(run_dir, facts, sections)
    print(f"Critique status: {report['status']}")
    return 0 if report["status"] != "fail" else 1


def cmd_render(args: argparse.Namespace) -> int:
    output = render_report(args.run_dir, out_path=args.out)
    print(f"Rendered HTML to {output}")
    return 0


def cmd_qa_html(args: argparse.Namespace) -> int:
    report = qa_rendered_html(args.run_dir, html_path=args.html_path)
    print(f"HTML QA status: {report['status']}")
    if report["failures"]:
        for failure in report["failures"]:
            print(f"- {failure}")
    return 0 if report["status"] == "pass" else 1


def cmd_run(args: argparse.Namespace) -> int:
    payload, report = _load_and_validate(args.input_path)
    if report.errors:
        _print_validation_errors(report)
        return 1
    provider_config = _provider_config_from_args(args)
    run_dir = args.run_dir or _default_run_dir(args.input_path)
    _prepare_run(run_dir, args.input_path, payload, provider_config)
    facts = _ensure_calculated(run_dir, payload)
    section_inputs = _load_or_build_section_inputs(run_dir, payload, facts)
    generate_sections(run_dir, section_inputs, provider_config, force=args.force)
    critique = critique_sections(run_dir, facts, load_generated_sections(run_dir))
    if critique.get("repair_candidates"):
        run_repair_if_needed(run_dir, section_inputs, provider_config, critique)
        critique = critique_sections(run_dir, facts, load_generated_sections(run_dir))
    output = render_report(run_dir)
    qa_report = qa_rendered_html(run_dir, html_path=output)
    print(f"Run directory: {run_dir}")
    print(f"Rendered HTML: {output}")
    print(f"Critique: {critique['status']}")
    print(f"HTML QA: {qa_report['status']}")
    return 0 if critique["status"] != "fail" and qa_report["status"] == "pass" else 1


def _provider_config_from_args(args: argparse.Namespace) -> ProviderConfig:
    return ProviderConfig(
        provider_kind=args.provider_kind,
        model=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        temperature=args.temperature,
        reasoning_effort=args.reasoning_effort,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
    )


def _load_and_validate(input_path: Path):
    payload = read_json(input_path)
    report = validate_client_payload(payload)
    return payload, report


def _prepare_run(run_dir: Path, input_path: Path, payload: dict, provider_config: ProviderConfig) -> None:
    init_run_layout(run_dir)
    manifest = load_manifest(run_dir)
    if not manifest:
        init_manifest(
            run_dir,
            client_id=payload["client_id"],
            provider_kind=provider_config.provider_kind,
            model=provider_config.model,
            input_path=input_path.resolve(),
            scenario_mode=SCENARIO_MODE_LOCKED,
        )
    write_json(run_dir / "client.input.json", payload)


def _ensure_calculated(run_dir: Path, payload: dict) -> dict:
    facts_path = run_dir / "facts.json"
    if facts_path.exists():
        return read_json(facts_path)
    facts = compute_facts(payload)
    write_json(facts_path, facts)
    section_inputs = build_section_inputs(payload, facts)
    for section_id, packet in section_inputs.items():
        write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)
    manifest = load_manifest(run_dir)
    manifest.setdefault("step_status", {})["calculate"] = "pass"
    save_manifest(run_dir, manifest)
    return facts


def _load_or_build_section_inputs(run_dir: Path, payload: dict, facts: dict) -> dict:
    existing = {}
    for section_file in sorted((run_dir / "section_inputs").glob("sec*.json")):
        existing[section_file.stem] = read_json(section_file)
    if len(existing) == 12:
        return existing
    built = build_section_inputs(payload, facts)
    for section_id, packet in built.items():
        write_json(run_dir / "section_inputs" / f"{section_id}.json", packet)
    return built


def _default_run_dir(input_path: Path) -> Path:
    payload = read_json(input_path)
    client_id = slugify(payload.get("client_id", input_path.stem))
    timestamp = utc_now_iso().replace(":", "-")
    return ensure_dir(Path("runs") / client_id / timestamp)


def _print_validation_errors(report) -> None:
    print("Validation failed:")
    for error in report.errors:
        print(f"- {error}")


if __name__ == "__main__":
    raise SystemExit(main())
