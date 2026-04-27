"""CLI entrypoint for the ADM pipeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from getpass import getpass
import json
import os
import sys
from pathlib import Path
from urllib import error, request

from adm_pipeline.constants import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_MODEL, DEFAULT_PROVIDER, DEFAULT_REASONING_EFFORT, DEFAULT_TEMPERATURE, DEFAULT_TIMEOUT_SECONDS, SCENARIO_MODE_LOCKED
from adm_pipeline.critique import critique_sections, load_generated_sections, run_repair_if_needed
from adm_pipeline.facts import build_section_inputs, compute_facts
from adm_pipeline.generation import generate_sections
from adm_pipeline.html_qa import qa_rendered_html
from adm_pipeline.provider_profiles import DEFAULT_PROFILES_PATH, list_profiles, load_profiles, resolve_profile
from adm_pipeline.providers import ProviderConfig
from adm_pipeline.render import render_report
from adm_pipeline.run_cleanup import list_runs, prune_runs
from adm_pipeline.run_state import init_manifest, init_run_layout, load_manifest, save_manifest
from adm_pipeline.utils import ensure_dir, read_json, slugify, utc_now_iso, write_json
from adm_pipeline.validation import validate_client_payload


LOCAL_ENV_PATH = Path(".adm.env")
SMOKE_SECTION_ID = "sec01"

GEMINI_MODEL_PRIORITY = {
    "gemma-4-31b-it": (0, "preferred: highest free-tier headroom"),
    "gemma-4-26b-a4b-it": (1, "preferred: strong free-tier headroom"),
    "gemma-3-27b-it": (2, "good headroom"),
    "gemma-3-12b-it": (3, "good headroom"),
    "gemma-3-4b-it": (4, "good headroom"),
    "gemma-3-1b-it": (5, "good headroom"),
    "gemma-3n-e4b-it": (6, "good headroom"),
    "gemma-3n-e2b-it": (7, "good headroom"),
    "gemini-2.5-flash-lite": (8, "usable but lower headroom than Gemma"),
    "gemini-flash-lite-latest": (9, "usable but can spike"),
    "gemini-2.0-flash-lite-001": (10, "usable but older"),
    "gemini-2.0-flash-lite": (11, "usable but older"),
    "gemini-2.5-flash": (50, "risky: low request budget"),
    "gemini-2.5-pro": (60, "avoid unless paid quota exists"),
    "gemini-pro-latest": (61, "avoid unless paid quota exists"),
    "gemini-3.1-pro-preview": (62, "avoid unless paid quota exists"),
    "gemini-3-pro-preview": (63, "avoid unless paid quota exists"),
    "gemini-3.1-flash-lite-preview": (64, "preview: can be unstable or overloaded"),
    "gemini-3-flash-preview": (65, "preview: can be unstable or overloaded"),
}


@dataclass
class DashboardState:
    input_path: Path | None
    profile_name: str | None
    profiles_config: Path
    runs_root: Path
    provider_overrides: dict[str, dict[str, object]]


def main(argv: list[str] | None = None) -> int:
    _load_local_env()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["dashboard"]
    elif argv and argv[0] in {"-d", "--dashboard"}:
        argv = ["dashboard", *argv[1:]]
    elif argv and argv[0] == "--doctor":
        argv = ["doctor", *argv[1:]]
    elif argv and _looks_like_input_path(argv[0]):
        argv = ["run", *argv]
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nExiting.")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adm", description="ADM pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dashboard_parser = subparsers.add_parser("dashboard", help="Show the operator dashboard")
    dashboard_parser.add_argument("input_path", type=Path, nargs="?")
    dashboard_parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    dashboard_parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    dashboard_parser.set_defaults(func=cmd_dashboard)

    validate_parser = subparsers.add_parser("validate", help="Validate a client ingress payload")
    validate_parser.add_argument("input_path", type=Path)
    validate_parser.set_defaults(func=cmd_validate)

    doctor_parser = subparsers.add_parser("doctor", help="Show provider/profile diagnostics")
    doctor_parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    doctor_parser.set_defaults(func=cmd_doctor)

    providers_parser = subparsers.add_parser("providers", help="List, inspect, and test named provider profiles")
    provider_actions = providers_parser.add_subparsers(dest="providers_command", required=True)

    provider_list_parser = provider_actions.add_parser("list", help="List provider profiles")
    provider_list_parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    provider_list_parser.set_defaults(func=cmd_providers_list)

    provider_show_parser = provider_actions.add_parser("show", help="Show a single provider profile")
    provider_show_parser.add_argument("profile_name")
    provider_show_parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    provider_show_parser.set_defaults(func=cmd_providers_show)

    provider_test_parser = provider_actions.add_parser("test", help="Test a provider profile")
    provider_test_parser.add_argument("profile_name")
    provider_test_parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    provider_test_parser.add_argument("--live", action="store_true")
    provider_test_parser.set_defaults(func=cmd_providers_test)

    runs_parser = subparsers.add_parser("runs", help="List and prune stored run directories")
    runs_actions = runs_parser.add_subparsers(dest="runs_command", required=True)

    runs_list_parser = runs_actions.add_parser("list", help="List runs for a client")
    runs_list_parser.add_argument("client_id")
    runs_list_parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    runs_list_parser.set_defaults(func=cmd_runs_list)

    runs_prune_parser = runs_actions.add_parser("prune", help="Keep only the newest N runs for a client")
    runs_prune_parser.add_argument("client_id")
    runs_prune_parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    runs_prune_parser.add_argument("--keep", type=int, default=2)
    runs_prune_parser.add_argument("--dry-run", action="store_true")
    runs_prune_parser.set_defaults(func=cmd_runs_prune)

    calculate_parser = subparsers.add_parser("calculate", help="Validate ingress and compute run facts")
    calculate_parser.add_argument("input_path", type=Path)
    calculate_parser.add_argument("--run-dir", type=Path, default=None)
    calculate_parser.add_argument("--label", default=None)
    add_provider_args(calculate_parser)
    calculate_parser.set_defaults(func=cmd_calculate)

    generate_parser = subparsers.add_parser("generate", help="Generate section payloads")
    generate_parser.add_argument("input_path", type=Path)
    generate_parser.add_argument("--run-dir", type=Path, required=True)
    generate_parser.add_argument("--force", action="store_true")
    add_provider_args(generate_parser)
    generate_parser.set_defaults(func=cmd_generate)

    smoke_parser = subparsers.add_parser("smoke", help="Run a single-section smoke test for the selected provider")
    smoke_parser.add_argument("input_path", type=Path)
    smoke_parser.add_argument("--run-dir", type=Path, default=None)
    smoke_parser.add_argument("--label", default=None)
    smoke_parser.add_argument("--force", action="store_true")
    smoke_parser.add_argument("--section-id", default=SMOKE_SECTION_ID)
    add_provider_args(smoke_parser)
    smoke_parser.set_defaults(func=cmd_smoke)

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
    run_parser.add_argument("--label", default=None)
    run_parser.add_argument("--force", action="store_true")
    run_parser.add_argument("--skip-smoke", action="store_true")
    add_provider_args(run_parser)
    run_parser.set_defaults(func=cmd_run)
    return parser


def add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", default=None)
    parser.add_argument("--profiles-config", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--provider", default=None, dest="provider_kind")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--max-output-tokens", type=int, default=None)


def cmd_dashboard(args: argparse.Namespace) -> int:
    state = DashboardState(
        input_path=args.input_path or _default_input_path(),
        profile_name=_choose_dashboard_default_profile(args.profiles_config),
        profiles_config=args.profiles_config,
        runs_root=args.runs_root,
        provider_overrides={},
    )
    if not sys.stdin.isatty():
        _print_dashboard_snapshot(state)
        return 0
    return _run_interactive_dashboard(state)


def _run_interactive_dashboard(state: DashboardState) -> int:
    while True:
        _print_dashboard_snapshot(state)
        print("Options:")
        print("  1. Provider setup / API key / test")
        print("  2. Ingress file selection / validation")
        print("  3. Prepare folder structure")
        print("  4. Run pipeline (real providers auto-smoke sec01 first)")
        print("  5. Runs cleanup / latest outputs")
        print("  6. Doctor diagnostics")
        print("  0. Exit")
        choice = input("Select option: ").strip().lower()
        if choice == "1":
            _dashboard_provider_menu(state)
        elif choice == "2":
            _dashboard_input_menu(state)
        elif choice == "3":
            _dashboard_prepare_folders(state)
        elif choice == "4":
            _dashboard_run_pipeline(state)
        elif choice == "5":
            _dashboard_runs_menu(state)
        elif choice == "6":
            cmd_doctor(argparse.Namespace(profiles_config=state.profiles_config))
            _pause()
        elif choice in {"0", "q", "quit", "exit"}:
            return 0
        else:
            print("Unknown option.")
            _pause()


def _print_dashboard_snapshot(state: DashboardState) -> None:
    payload = _safe_payload(state.input_path)
    client_id = payload.get("client_id") if payload else None
    default_profile, profiles = list_profiles(state.profiles_config)
    selected_profile = state.profile_name or default_profile
    print()
    print("ADM dashboard")
    print(f"- Repo root: {Path.cwd()}")
    print(f"- Selected input: {state.input_path if state.input_path else '<none>'}")
    print(f"- Selected profile: {selected_profile or '<none>'}")
    if payload:
        print(f"- Client: {payload['company']['name']} ({payload['client_id']})")
    print(f"- Runs root: {state.runs_root / payload['client_id']}")
    active_overrides = _current_provider_overrides(state)
    if active_overrides:
        override_text = ", ".join(f"{key}={value}" for key, value in active_overrides.items())
        print(f"- Provider overrides: {override_text}")
    print("- Providers:")
    for name, profile in _ordered_profile_items(profiles):
        marker = "*" if name == selected_profile else " "
        status = _provider_dashboard_status(profile.get("provider_kind"), profile)
        print(f"  {marker} {_profile_display_name(name, profile)}: {profile.get('provider_kind')} / {profile.get('model')} [{status}]")
    if client_id:
        runs = list_runs(state.runs_root / client_id)
        print("- Latest runs:")
        if runs:
            for item in runs[:3]:
                print(f"  - {item['name']}")
        else:
            print("  - none")
    print("- Notes:")
    print("  - LM Studio local does not require an API key.")
    print("  - `adm <input.json>` is shorthand for `adm run <input.json>`.")
    print()


def _dashboard_provider_menu(state: DashboardState) -> None:
    while True:
        default_profile, profiles = list_profiles(state.profiles_config)
        selected = state.profile_name or default_profile
        ordered_items = _ordered_profile_items(profiles)
        print()
        print("Provider setup")
        names = [name for name, _profile in ordered_items]
        for index, (name, profile) in enumerate(ordered_items, start=1):
            marker = "*" if name == selected else " "
            status = _provider_dashboard_status(profile.get("provider_kind"), profile)
            overrides = state.provider_overrides.get(name, {})
            suffix = f" overrides={overrides}" if overrides else ""
            print(f"  {index}. {marker} {_profile_display_name(name, profile)} -> {profile.get('provider_kind')} / {profile.get('model')} [{status}]{suffix}")
        print("  s. Select provider by number")
        print("  k. Enter or update API key for selected provider")
        print("  t. Test selected provider")
        print("  m. Set model override")
        print("  l. List and select available models (rate-aware)")
        print("  p. Set temperature override")
        print("  x. Set max output tokens override")
        print("  u. Set base URL override")
        print("  c. Clear overrides for selected provider")
        print("  b. Back")
        choice = input("Select option: ").strip().lower()
        if choice.isdigit():
            chosen = _select_profile_by_number(names, choice)
            if chosen:
                state.profile_name = chosen
                print(f"Selected provider: {_profile_display_name(chosen, profiles[chosen])}")
            else:
                print("Invalid selection.")
            _pause()
        elif choice == "s":
            state.profile_name = _prompt_select_profile(profiles, selected)
        elif choice == "k":
            _prompt_provider_key(state, profiles, selected)
        elif choice == "t":
            _test_selected_provider(state, selected, live=True)
            _pause()
        elif choice == "m":
            _prompt_model_override(state, profiles, selected)
        elif choice == "l":
            _prompt_available_model_override(state, profiles, selected)
        elif choice == "p":
            _prompt_float_override(state, selected, "temperature")
        elif choice == "x":
            _prompt_int_override(state, selected, "max_output_tokens")
        elif choice == "u":
            _prompt_text_override(state, selected, "base_url")
        elif choice == "c":
            if selected and selected in state.provider_overrides:
                state.provider_overrides.pop(selected, None)
                print("Overrides cleared.")
            else:
                print("No overrides to clear.")
            _pause()
        elif choice in {"b", "0"}:
            return
        else:
            print("Unknown option.")
            _pause()


def _dashboard_input_menu(state: DashboardState) -> None:
    while True:
        print()
        print("Ingress selection")
        discovered = _discover_inputs()
        if discovered:
            for index, path in enumerate(discovered, start=1):
                marker = "*" if state.input_path and path.resolve() == state.input_path.resolve() else " "
                print(f"  {index}. {marker} {path}")
        else:
            print("  No ingress files found in inputs/clients")
        print("  s. Select file")
        print("  v. Validate selected file")
        print("  p. Print selected file path")
        print("  b. Back")
        choice = input("Select option: ").strip().lower()
        if choice == "s":
            state.input_path = _prompt_select_input(discovered, state.input_path)
        elif choice == "v":
            if not state.input_path:
                print("No input selected.")
            else:
                exit_code = cmd_validate(argparse.Namespace(input_path=state.input_path))
                if exit_code == 0:
                    print("Selected ingress is valid.")
            _pause()
        elif choice == "p":
            print(f"Selected input: {state.input_path if state.input_path else '<none>'}")
            _pause()
        elif choice in {"b", "0"}:
            return
        else:
            print("Unknown option.")
            _pause()


def _dashboard_prepare_folders(state: DashboardState) -> None:
    payload = _require_selected_payload(state)
    if payload is None:
        _pause()
        return
    provider_config = _resolve_selected_provider(state)
    client_root = ensure_dir(state.runs_root / payload["client_id"])
    next_run = _default_run_dir(state.input_path, provider_config=provider_config, label="prepared-preview")
    if next_run.exists():
        try:
            next_run.rmdir()
        except OSError:
            pass
    print()
    print("Folder structure prepared")
    print(f"- Client runs root ensured: {client_root}")
    print(f"- Next auto run name preview: {next_run}")
    _pause()


def _dashboard_run_pipeline(state: DashboardState) -> None:
    payload = _require_selected_payload(state)
    if payload is None:
        _pause()
        return
    provider_config = _resolve_selected_provider(state)
    label = input("Run label (optional, blank for none): ").strip() or None
    run_mode = input("Run mode: [F]ull pipeline or [S]moke sec01 only? [F]: ").strip().lower() or "f"
    common_args = argparse.Namespace(
        input_path=state.input_path,
        run_dir=None,
        label=label,
        force=False,
        profile=state.profile_name,
        profiles_config=state.profiles_config,
        provider_kind=provider_config.provider_kind,
        model=provider_config.model,
        base_url=provider_config.base_url,
        api_key_env=provider_config.api_key_env,
        temperature=provider_config.temperature,
        reasoning_effort=provider_config.reasoning_effort,
        timeout_seconds=provider_config.timeout_seconds,
        max_retries=provider_config.max_retries,
        max_output_tokens=provider_config.max_output_tokens,
        skip_smoke=False,
        section_id=SMOKE_SECTION_ID,
    )
    if run_mode == "s":
        cmd_smoke(common_args)
    else:
        cmd_run(common_args)
    _pause()


def _dashboard_runs_menu(state: DashboardState) -> None:
    payload = _require_selected_payload(state)
    if payload is None:
        _pause()
        return
    client_id = payload["client_id"]
    while True:
        runs = list_runs(state.runs_root / client_id)
        print()
        print(f"Runs for {client_id}")
        if runs:
            for item in runs[:10]:
                print(f"  - {item['name']}")
        else:
            print("  - none")
        print("  p. Prune old runs")
        print("  h. Show latest HTML path")
        print("  b. Back")
        choice = input("Select option: ").strip().lower()
        if choice == "p":
            keep_raw = input("Keep how many newest runs? [2]: ").strip()
            keep = int(keep_raw) if keep_raw else 2
            cmd_runs_prune(argparse.Namespace(client_id=client_id, runs_root=state.runs_root, keep=keep, dry_run=False))
            _pause()
        elif choice == "h":
            if runs:
                latest_html = Path(state.runs_root / client_id / str(runs[0]["name"]) / "final" / f"{client_id}.html")
                print(f"Latest HTML: {latest_html}")
            else:
                print("No runs available.")
            _pause()
        elif choice in {"b", "0"}:
            return
        else:
            print("Unknown option.")
            _pause()


def _prompt_select_profile(profiles: dict, selected: str | None) -> str | None:
    raw = input("Enter provider number: ").strip()
    if not raw:
        return selected
    chosen = _select_profile_by_number(list(profiles.keys()), raw)
    if chosen:
        print(f"Selected provider: {chosen}")
        return chosen
    print("Invalid number.")
    return selected


def _prompt_provider_key(state: DashboardState, profiles: dict, selected: str | None) -> None:
    if not selected or selected not in profiles:
        print("No provider selected.")
        _pause()
        return
    profile = profiles[selected]
    provider_kind = profile.get("provider_kind")
    env_name = profile.get("api_key_env")
    if provider_kind == "lmstudio_openai_compat" or not env_name:
        print("Selected provider does not use an API key.")
        _pause()
        return
    value = getpass(f"Enter {env_name} (saved to {LOCAL_ENV_PATH} and loaded next launch): ").strip()
    if not value:
        print("No key entered.")
        _pause()
        return
    os.environ[env_name] = value
    _save_local_env_var(env_name, value)
    print(f"{env_name} saved to {LOCAL_ENV_PATH} and set for this dashboard session.")
    ok, message = _test_provider_config(resolve_profile(profile_name=selected, config_path=state.profiles_config, overrides={}), live=False)
    print(message)
    if ok:
        live_choice = input("Run live provider test now? [y/N]: ").strip().lower()
        if live_choice == "y":
            ok, message = _test_provider_config(_resolve_selected_provider(state), live=True)
            print(message)
    _pause()


def _test_selected_provider(state: DashboardState, selected: str | None, *, live: bool) -> None:
    if not selected:
        print("No provider selected.")
        return
    provider_config = _resolve_selected_provider(state)
    ok, message = _test_provider_config(provider_config, live=live)
    print(message)
    if not ok and provider_config.api_key_env and not os.environ.get(provider_config.api_key_env):
        print(f"Tip: set {provider_config.api_key_env} from option 1.")


def _prompt_model_override(state: DashboardState, profiles: dict, selected: str | None) -> None:
    if not selected or selected not in profiles:
        print("No provider selected.")
        _pause()
        return
    current = _resolve_selected_provider(state).model
    value = input(f"Model override [{current}]: ").strip()
    if not value:
        print("Model unchanged.")
    else:
        _set_provider_override(state, selected, "model", value)
        print(f"Model override set: {value}")
    _pause()


def _prompt_available_model_override(state: DashboardState, profiles: dict, selected: str | None) -> None:
    if not selected or selected not in profiles:
        print("No provider selected.")
        _pause()
        return
    profile = profiles[selected]
    provider_kind = profile.get("provider_kind")
    models: list[str] = []
    if provider_kind == "lmstudio_openai_compat":
        models = _list_lmstudio_models(profile.get("base_url") or "http://127.0.0.1:1234/v1")
    elif provider_kind == "gemini":
        config = _resolve_selected_provider(state)
        models = _list_gemini_models(config)
    elif provider_kind == "openrouter":
        config = _resolve_selected_provider(state)
        free_only = input("Show free-capable models only? [Y/n]: ").strip().lower() not in {"n", "no"}
        models = _list_openrouter_models(config, free_only=free_only)
    else:
        print("Selected provider does not support remote model listing.")
        _pause()
        return
    if not models:
        print("No models discovered for the selected provider.")
        _pause()
        return
    print("Available models:")
    for index, model in enumerate(models, start=1):
        note = _model_selection_note(provider_kind, model)
        suffix = f" [{note}]" if note else ""
        print(f"  {index}. {model}{suffix}")
    raw = input("Choose model number: ").strip()
    if not raw:
        _pause()
        return
    try:
        index = int(raw) - 1
    except ValueError:
        print("Invalid number.")
        _pause()
        return
    if 0 <= index < len(models):
        chosen = models[index]
        _set_provider_override(state, selected, "model", chosen)
        print(f"Model override set: {chosen}")
    else:
        print("Invalid selection.")
    _pause()


def _prompt_float_override(state: DashboardState, selected: str | None, key: str) -> None:
    if not selected:
        print("No provider selected.")
        _pause()
        return
    current = getattr(_resolve_selected_provider(state), key)
    raw = input(f"{key} override [{current}]: ").strip()
    if not raw:
        print(f"{key} unchanged.")
        _pause()
        return
    try:
        value = float(raw)
    except ValueError:
        print("Invalid number.")
        _pause()
        return
    _set_provider_override(state, selected, key, value)
    print(f"{key} override set: {value}")
    _pause()


def _prompt_int_override(state: DashboardState, selected: str | None, key: str) -> None:
    if not selected:
        print("No provider selected.")
        _pause()
        return
    current = getattr(_resolve_selected_provider(state), key)
    raw = input(f"{key} override [{current}]: ").strip()
    if not raw:
        print(f"{key} unchanged.")
        _pause()
        return
    try:
        value = int(raw)
    except ValueError:
        print("Invalid integer.")
        _pause()
        return
    _set_provider_override(state, selected, key, value)
    print(f"{key} override set: {value}")
    _pause()


def _prompt_text_override(state: DashboardState, selected: str | None, key: str) -> None:
    if not selected:
        print("No provider selected.")
        _pause()
        return
    current = getattr(_resolve_selected_provider(state), key) or ""
    raw = input(f"{key} override [{current}]: ").strip()
    if not raw:
        print(f"{key} unchanged.")
        _pause()
        return
    _set_provider_override(state, selected, key, raw)
    print(f"{key} override set: {raw}")
    _pause()


def _prompt_select_input(discovered: list[Path], current: Path | None) -> Path | None:
    raw = input("Enter ingress number or full path: ").strip()
    if not raw:
        return current
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(discovered):
            selected = discovered[index]
            print(f"Selected input: {selected}")
            return selected
        print("Invalid selection.")
        return current
    candidate = Path(raw)
    if candidate.exists() and candidate.suffix.lower() == ".json":
        print(f"Selected input: {candidate}")
        return candidate
    print("Input path not found or not a JSON file.")
    return current


def _require_selected_payload(state: DashboardState) -> dict | None:
    payload = _safe_payload(state.input_path)
    if payload is None:
        print("No valid input selected.")
    return payload


def _safe_payload(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:  # noqa: BLE001
        return None


def _resolve_selected_provider(state: DashboardState) -> ProviderConfig:
    return resolve_profile(
        profile_name=state.profile_name,
        config_path=state.profiles_config,
        overrides=_current_provider_overrides(state),
    )


def _pause() -> None:
    if sys.stdin.isatty():
        input("Press Enter to continue...")


def _current_provider_overrides(state: DashboardState) -> dict[str, object]:
    if not state.profile_name:
        return {}
    return dict(state.provider_overrides.get(state.profile_name, {}))


def _set_provider_override(state: DashboardState, profile_name: str, key: str, value: object) -> None:
    overrides = state.provider_overrides.setdefault(profile_name, {})
    overrides[key] = value


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


def cmd_doctor(args: argparse.Namespace) -> int:
    default_profile, profiles = list_profiles(args.profiles_config)
    print("ADM doctor")
    print(f"- Profiles config: {args.profiles_config}")
    print(f"- Default profile: {default_profile or '<none>'}")
    if profiles:
        print("- Profiles:")
        for name, profile in profiles.items():
            print(f"  - {name}: {profile.get('provider_kind')} / {profile.get('model')}")
    else:
        print("- Profiles: none")
    print("- Environment:")
    for env_name in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        print(f"  - {env_name}: {'set' if os.environ.get(env_name) else 'missing'}")
    print("  - LM Studio local auth: not required")
    lmstudio_ok, lmstudio_message = _probe_lmstudio()
    print(f"- LM Studio: {'ok' if lmstudio_ok else 'unavailable'}")
    print(f"  {lmstudio_message}")
    return 0


def cmd_providers_list(args: argparse.Namespace) -> int:
    default_profile, profiles = list_profiles(args.profiles_config)
    if not profiles:
        print("No provider profiles configured.")
        return 0
    print(f"Default profile: {default_profile or '<none>'}")
    for name, profile in profiles.items():
        marker = "*" if name == default_profile else " "
        print(f"{marker} {name}: {profile.get('provider_kind')} / {profile.get('model')}")
    return 0


def cmd_providers_show(args: argparse.Namespace) -> int:
    payload = load_profiles(args.profiles_config)
    profile = payload.get("profiles", {}).get(args.profile_name)
    if not profile:
        print(f"Unknown profile: {args.profile_name}", file=sys.stderr)
        return 1
    print(json.dumps(profile, indent=2))
    return 0


def cmd_providers_test(args: argparse.Namespace) -> int:
    provider_config = resolve_profile(profile_name=args.profile_name, config_path=args.profiles_config, overrides={})
    ok, message = _test_provider_config(provider_config, live=args.live)
    print(message)
    return 0 if ok else 1


def cmd_runs_list(args: argparse.Namespace) -> int:
    client_root = args.runs_root / args.client_id
    runs = list_runs(client_root)
    if not runs:
        print(f"No runs found in {client_root}")
        return 0
    print(f"Runs for {args.client_id}:")
    for item in runs:
        print(f"- {item['name']}")
    return 0


def cmd_runs_prune(args: argparse.Namespace) -> int:
    client_root = args.runs_root / args.client_id
    report = prune_runs(client_root, keep=args.keep, dry_run=args.dry_run)
    action = "Would delete" if args.dry_run else "Deleted"
    print(f"Client runs root: {client_root}")
    print(f"Keeping newest: {args.keep}")
    if report["kept"]:
        print("Kept:")
        for item in report["kept"]:
            print(f"- {item['name']}")
    else:
        print("Kept: none")
    if report["deleted"]:
        print(f"{action}:")
        for item in report["deleted"]:
            print(f"- {item['name']}")
    else:
        print(f"{action}: none")
    return 0


def cmd_calculate(args: argparse.Namespace) -> int:
    provider_config = _provider_config_from_args(args)
    run_dir = args.run_dir or _default_run_dir(args.input_path, provider_config=provider_config, label=args.label)
    payload, report = _load_and_validate(args.input_path)
    if report.errors:
        _print_validation_errors(report)
        return 1
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


def cmd_smoke(args: argparse.Namespace) -> int:
    payload, report = _load_and_validate(args.input_path)
    if report.errors:
        _print_validation_errors(report)
        return 1
    provider_config = _provider_config_from_args(args)
    run_dir = args.run_dir or _default_run_dir(args.input_path, provider_config=provider_config, label=args.label or "smoke")
    _prepare_run(run_dir, args.input_path, payload, provider_config)
    facts = _ensure_calculated(run_dir, payload)
    section_inputs = _load_or_build_section_inputs(run_dir, payload, facts)
    section_id = args.section_id
    if section_id not in section_inputs:
        print(f"Unknown section id: {section_id}", file=sys.stderr)
        return 1
    result = _run_provider_smoke(run_dir, section_inputs, provider_config, section_id=section_id, force=args.force)
    print(f"Smoke test status: {result['status']}")
    print(f"Run directory: {run_dir}")
    if result.get("error"):
        print(f"- {result['error']}")
    return 0 if result["status"] == "pass" else 1


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
    run_dir = args.run_dir or _default_run_dir(args.input_path, provider_config=provider_config, label=args.label)
    _prepare_run(run_dir, args.input_path, payload, provider_config)
    facts = _ensure_calculated(run_dir, payload)
    section_inputs = _load_or_build_section_inputs(run_dir, payload, facts)
    if _requires_live_smoke(provider_config) and not args.skip_smoke:
        smoke = _run_provider_smoke(run_dir, section_inputs, provider_config, section_id=SMOKE_SECTION_ID, force=args.force)
        print(f"Smoke test ({SMOKE_SECTION_ID}): {smoke['status']}")
        if smoke["status"] != "pass":
            if smoke.get("error"):
                print(f"- {smoke['error']}")
            return 1
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


def _requires_live_smoke(provider_config: ProviderConfig) -> bool:
    return provider_config.provider_kind != "mock"


def _run_provider_smoke(
    run_dir: Path,
    section_inputs: dict[str, dict],
    provider_config: ProviderConfig,
    *,
    section_id: str,
    force: bool,
) -> dict[str, object]:
    manifest = load_manifest(run_dir)
    smoke_key = f"{provider_config.provider_kind}:{provider_config.model}:{section_id}"
    smoke_state = manifest.setdefault("smoke_tests", {})
    cached = smoke_state.get(smoke_key)
    if cached and cached.get("status") == "pass" and not force:
        return cached
    try:
        generate_sections(run_dir, {section_id: section_inputs[section_id]}, provider_config, force=force)
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "fail",
            "section_id": section_id,
            "provider_kind": provider_config.provider_kind,
            "model": provider_config.model,
            "error": str(exc),
            "updated_at": utc_now_iso(),
        }
        smoke_state[smoke_key] = result
        manifest.setdefault("step_status", {})["smoke"] = "fail"
        save_manifest(run_dir, manifest)
        return result
    result = {
        "status": "pass",
        "section_id": section_id,
        "provider_kind": provider_config.provider_kind,
        "model": provider_config.model,
        "error": None,
        "updated_at": utc_now_iso(),
    }
    smoke_state[smoke_key] = result
    manifest.setdefault("step_status", {})["smoke"] = "pass"
    save_manifest(run_dir, manifest)
    return result


def _provider_config_from_args(args: argparse.Namespace) -> ProviderConfig:
    overrides = {
        "provider_kind": args.provider_kind,
        "model": args.model,
        "base_url": args.base_url,
        "api_key_env": args.api_key_env,
        "temperature": args.temperature,
        "reasoning_effort": args.reasoning_effort,
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "max_output_tokens": args.max_output_tokens,
    }
    explicit_override_present = any(value is not None for value in overrides.values())
    try:
        return resolve_profile(
            profile_name=getattr(args, "profile", None),
            config_path=getattr(args, "profiles_config", DEFAULT_PROFILES_PATH),
            use_default_profile=not explicit_override_present or getattr(args, "profile", None) is not None,
            overrides=overrides,
        )
    except RuntimeError:
        if getattr(args, "profile", None) or (getattr(args, "profiles_config", DEFAULT_PROFILES_PATH).exists()):
            raise
        return ProviderConfig(
            provider_kind=args.provider_kind or DEFAULT_PROVIDER,
            model=args.model or DEFAULT_MODEL,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            temperature=args.temperature if args.temperature is not None else DEFAULT_TEMPERATURE,
            reasoning_effort=args.reasoning_effort or DEFAULT_REASONING_EFFORT,
            timeout_seconds=args.timeout_seconds if args.timeout_seconds is not None else DEFAULT_TIMEOUT_SECONDS,
            max_retries=args.max_retries if args.max_retries is not None else 2,
            max_output_tokens=args.max_output_tokens if args.max_output_tokens is not None else DEFAULT_MAX_OUTPUT_TOKENS,
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
            profile_name=provider_config.profile_name,
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


def _default_run_dir(input_path: Path, *, provider_config: ProviderConfig | None = None, label: str | None = None) -> Path:
    payload = read_json(input_path)
    client_id = slugify(payload.get("client_id", input_path.stem))
    timestamp = _run_timestamp_slug()
    profile_slug = slugify((provider_config.profile_name or provider_config.provider_kind) if provider_config else "run")
    parts = [timestamp, profile_slug]
    if label:
        parts.append(slugify(label))
    run_name = "__".join(part for part in parts if part)
    return ensure_dir(Path("runs") / client_id / run_name)


def _print_validation_errors(report) -> None:
    print("Validation failed:")
    for error in report.errors:
        print(f"- {error}")


def _probe_lmstudio(base_url: str = "http://127.0.0.1:1234/v1") -> tuple[bool, str]:
    model_ids = _list_lmstudio_models(base_url)
    if not model_ids:
        url = base_url.rstrip("/") + "/models"
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
        model_ids = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]
        if not model_ids:
            return True, "Server reachable but no models listed."
    return True, "Models: " + ", ".join(model_ids)


def _list_lmstudio_models(base_url: str = "http://127.0.0.1:1234/v1") -> list[str]:
    url = base_url.rstrip("/") + "/models"
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return []
    model_ids = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]
    return [model_id for model_id in model_ids if model_id]


def _list_gemini_models(config: ProviderConfig) -> list[str]:
    env_name = config.api_key_env or "GEMINI_API_KEY"
    api_key = os.environ.get(env_name)
    if not api_key:
        print(f"{env_name} is not set.")
        return []
    base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    url = f"{base_url}/models?pageSize=1000"
    req = request.Request(url, headers={"x-goog-api-key": api_key}, method="GET")
    try:
        with request.urlopen(req, timeout=min(config.timeout_seconds, 30)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini model list failed: {exc}")
        return []
    model_names = []
    for item in payload.get("models", []):
        if not isinstance(item, dict):
            continue
        if "generateContent" not in item.get("supportedGenerationMethods", []):
            continue
        name = item.get("name", "")
        if name.startswith("models/"):
            name = name.split("/", 1)[1]
        if name:
            model_names.append(name)
    return _sort_available_models("gemini", model_names)


def _list_openrouter_models(config: ProviderConfig, *, free_only: bool) -> list[str]:
    env_name = config.api_key_env or "OPENROUTER_API_KEY"
    api_key = os.environ.get(env_name)
    if not api_key:
        print(f"{env_name} is not set.")
        return []
    url = (config.base_url or "https://openrouter.ai/api/v1").rstrip("/") + "/models"
    req = request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=min(config.timeout_seconds, 30)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"OpenRouter model list failed: {exc}")
        return []
    models = []
    for item in payload.get("data", []):
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        if free_only and not _is_openrouter_free_model(item):
            continue
        models.append(model_id)
    if free_only and "openrouter/free" not in models:
        models.insert(0, "openrouter/free")
    return _sort_available_models("openrouter", sorted(set(models)))


def _is_openrouter_free_model(item: dict) -> bool:
    model_id = item.get("id", "")
    if isinstance(model_id, str) and model_id.endswith(":free"):
        return True
    pricing = item.get("pricing", {})
    if not isinstance(pricing, dict):
        return False
    free_fields = ("prompt", "completion", "request")
    return all(str(pricing.get(field, "")).strip() == "0" for field in free_fields)


def _sort_available_models(provider_kind: str, models: list[str]) -> list[str]:
    unique = list(dict.fromkeys(models))
    if provider_kind == "gemini":
        return sorted(unique, key=_gemini_model_sort_key)
    if provider_kind == "openrouter":
        return sorted(unique, key=_openrouter_model_sort_key)
    return sorted(unique)


def _gemini_model_sort_key(model: str) -> tuple[int, str]:
    rank, _note = GEMINI_MODEL_PRIORITY.get(model, (30, ""))
    return rank, model


def _openrouter_model_sort_key(model: str) -> tuple[int, str]:
    if model == "openrouter/free":
        return (0, model)
    if model.endswith(":free"):
        return (1, model)
    if "gemma" in model.lower():
        return (2, model)
    return (20, model)


def _model_selection_note(provider_kind: str, model: str) -> str:
    if provider_kind == "gemini":
        return GEMINI_MODEL_PRIORITY.get(model, (0, ""))[1]
    if provider_kind == "openrouter":
        if model == "openrouter/free":
            return "router picks current free model"
        if model.endswith(":free"):
            return "free model"
    return ""


def _test_provider_config(config: ProviderConfig, *, live: bool) -> tuple[bool, str]:
    env_name = config.api_key_env
    if config.provider_kind == "mock":
        return True, "mock profile is ready."
    if config.provider_kind == "lmstudio_openai_compat":
        ok, message = _probe_lmstudio(config.base_url or "http://127.0.0.1:1234/v1")
        if not ok:
            return False, f"LM Studio test failed: {message}"
        return True, f"LM Studio reachable. {message}"
    if env_name and not os.environ.get(env_name):
        return False, f"Missing required environment variable {env_name}."
    if not live:
        return True, f"{config.provider_kind} profile is configured. Use --live to send a real request."
    if config.provider_kind == "gemini":
        return _live_test_gemini(config)
    if config.provider_kind == "openrouter":
        return _live_test_openrouter(config)
    if config.provider_kind == "openai_responses":
        return True, "OpenAI profile configured; live test is not implemented in this CLI."
    return False, f"Unknown provider kind {config.provider_kind}"


def _live_test_gemini(config: ProviderConfig) -> tuple[bool, str]:
    api_key = os.environ.get(config.api_key_env or "GEMINI_API_KEY")
    base_url = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    url = f"{base_url}/models/{config.model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": "Return JSON {\"ok\":true,\"provider\":\"gemini\"}"}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 64,
            "responseMimeType": "application/json",
            "responseJsonSchema": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "provider": {"type": "string"},
                },
                "required": ["ok", "provider"],
                "additionalProperties": False,
            },
        },
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=min(config.timeout_seconds, 30)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return False, f"Gemini live test failed: HTTP {exc.code}: {details}"
    except Exception as exc:  # noqa: BLE001
        return False, f"Gemini live test failed: {exc}"
    text_output = response_payload.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
    return True, f"Gemini live test succeeded: {text_output}"


def _live_test_openrouter(config: ProviderConfig) -> tuple[bool, str]:
    api_key = os.environ.get(config.api_key_env or "OPENROUTER_API_KEY")
    url = (config.base_url or "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": "Return exactly this JSON: {\"ok\":true,\"provider\":\"openrouter\"}"}],
        "temperature": 0,
        "max_tokens": 64,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "healthcheck",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "provider": {"type": "string"},
                    },
                    "required": ["ok", "provider"],
                    "additionalProperties": False,
                },
            },
        },
    }
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=min(config.timeout_seconds, 30)) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return False, f"OpenRouter live test failed: HTTP {exc.code}: {details}"
    except Exception as exc:  # noqa: BLE001
        return False, f"OpenRouter live test failed: {exc}"
    text_output = response_payload.get("choices", [{}])[0].get("message", {}).get("content")
    return True, f"OpenRouter live test succeeded: {text_output}"


def _run_timestamp_slug() -> str:
    return utc_now_iso().replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")


def _default_input_path() -> Path | None:
    preferred = Path("inputs/clients/northstar-retail.json")
    if preferred.exists():
        return preferred
    discovered = _discover_inputs()
    return discovered[0] if discovered else None


def _discover_inputs() -> list[Path]:
    root = Path("inputs") / "clients"
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def _looks_like_input_path(value: str) -> bool:
    if value.startswith("-"):
        return False
    path = Path(value)
    return path.suffix.lower() == ".json" and path.exists()


def _provider_dashboard_status(provider_kind: str | None, profile: dict) -> str:
    if provider_kind == "mock":
        return "ready"
    if provider_kind == "lmstudio_openai_compat":
        ok, _message = _probe_lmstudio(profile.get("base_url") or "http://127.0.0.1:1234/v1")
        return "local-ok" if ok else "local-offline"
    env_name = profile.get("api_key_env")
    if env_name and os.environ.get(env_name):
        return f"{env_name} set"
    if env_name:
        return f"{env_name} missing"
    return "configured"


def _ordered_profile_items(profiles: dict[str, dict]) -> list[tuple[str, dict]]:
    def sort_key(item: tuple[str, dict]) -> tuple[int, str]:
        name, profile = item
        kind = profile.get("provider_kind")
        if kind == "openrouter":
            return (0, name)
        if kind == "gemini":
            return (1, name)
        if kind == "lmstudio_openai_compat":
            return (2, name)
        if kind == "mock":
            return (9, name)
        return (5, name)

    return sorted(profiles.items(), key=sort_key)


def _select_profile_by_number(names: list[str], raw: str) -> str | None:
    try:
        index = int(raw) - 1
    except ValueError:
        return None
    if 0 <= index < len(names):
        return names[index]
    return None


def _profile_display_name(name: str, profile: dict) -> str:
    provider_kind = profile.get("provider_kind")
    if provider_kind == "mock":
        return f"{name} [pipeline self-test]"
    if provider_kind == "lmstudio_openai_compat":
        return f"{name} [real local model]"
    return name


def _choose_dashboard_default_profile(config_path: Path) -> str | None:
    default_profile, profiles = list_profiles(config_path)
    for name, profile in _ordered_profile_items(profiles):
        status = _provider_dashboard_status(profile.get("provider_kind"), profile)
        if status in {"OPENROUTER_API_KEY set", "GEMINI_API_KEY set", "local-ok"}:
            return name
    return default_profile


def _load_local_env() -> None:
    if not LOCAL_ENV_PATH.exists():
        return
    for raw_line in LOCAL_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def _save_local_env_var(key: str, value: str) -> None:
    existing: dict[str, str] = {}
    if LOCAL_ENV_PATH.exists():
        for raw_line in LOCAL_ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, env_value = line.split("=", 1)
            existing[env_key.strip()] = env_value.strip()
    existing[key] = value
    lines = [f"{env_key}={env_value}" for env_key, env_value in sorted(existing.items())]
    LOCAL_ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
