# ADM Pipeline

Structured-ingress pipeline for generating Account Development Master HTML reports from client JSON.

## What It Does

- Validates frozen `schema_version: "2.0"` ingress payloads
- Computes all financial facts in code
- Builds `section_inputs/sec01.json` through `sec12.json`
- Generates 12 structured section payloads through a provider adapter
- Runs a critique and targeted repair pass
- Renders one self-contained HTML report
- Runs final HTML QA on the rendered artifact

## Providers

- `gemini`
- `openai_responses`
- `lmstudio_openai_compat`
- `openrouter`
- `mock` for deterministic local smoke tests

Named provider profiles live in [config/providers.json](/C:/Users/Lielina/Desktop/Projects/ADM%20Automation%20Platform/config/providers.json). The `mock` profile exists for local verification and CI-like runs without network access.

## Install

```powershell
python -m pip install -e .
```

If you do not want to install the console script yet, run the CLI from the repo root with either:

```powershell
python -m adm_pipeline.cli dashboard
python -m adm_pipeline.cli doctor
.\adm.cmd dashboard
.\adm.cmd doctor
```

Optional provider dependencies:

```powershell
python -m pip install -e .[providers]
```

Only the hosted OpenAI adapter needs the optional Python provider package. Gemini, OpenRouter, and LM Studio use direct HTTP in this repo.

## Provider CLI

Show diagnostics:

```powershell
adm dashboard
adm doctor
adm -d
```

`adm -d` now opens the interactive CLI dashboard in a normal terminal. The dashboard lets you:
- press `1` for provider setup, API key entry, and provider tests
- press `2` to choose or validate the ingress file
- press `3` to prepare the folder structure
- press `4` to run the pipeline
- press `5` to prune or inspect runs

If stdin is non-interactive, the same command falls back to a plain status summary.

List profiles:

```powershell
adm providers list
```

Show one profile:

```powershell
adm providers show gemini-main
```

Test one profile:

```powershell
adm providers test lmstudio-local
adm providers test gemini-main
adm providers test openrouter-main --live
```

## Run Management

List runs for one client:

```powershell
adm runs list northstar-retail
```

Dry-run cleanup to keep only the newest two:

```powershell
adm runs prune northstar-retail --keep 2 --dry-run
```

Apply the cleanup:

```powershell
adm runs prune northstar-retail --keep 2
```

## Example Commands

Validate ingress:

```powershell
adm validate inputs/clients/northstar-retail.json
```

Run the full local deterministic pipeline:

```powershell
adm run inputs/clients/northstar-retail.json --profile mock-local --run-dir runs/northstar-retail/local-smoke
```

Shorthand from the repo root:

```powershell
.\adm.cmd inputs\clients\northstar-retail.json --profile mock-local
```

That is equivalent to:

```powershell
.\adm.cmd run inputs\clients\northstar-retail.json --profile mock-local
```

If you omit `--run-dir`, the CLI now creates standardized names like:

```text
runs/northstar-retail/20260427-072215__mock-local
```

Run generation only:

```powershell
adm generate inputs/clients/northstar-retail.json --profile mock-local --run-dir runs/northstar-retail/local-smoke
```

Run with Gemini:

```powershell
$env:GEMINI_API_KEY="..."
adm run inputs/clients/northstar-retail.json --profile gemini-main --run-dir runs/northstar-retail/gemini
```

Run with LM Studio:

```powershell
adm run inputs/clients/northstar-retail.json --profile lmstudio-local --run-dir runs/northstar-retail/lmstudio
```

Render the final HTML:

```powershell
adm render --run-dir runs/northstar-retail/local-smoke
```

Run final HTML QA:

```powershell
adm qa-html --run-dir runs/northstar-retail/local-smoke
```

## Run Artifacts

- `manifest.json`
- `facts.json`
- `section_inputs/secNN.json`
- `sections/secNN.request.json`
- `sections/secNN.raw.json`
- `sections/secNN.normalized.json`
- `critique/global_critique.json`
- `critique/repair_actions.json`
- `final/<client_id>.html`
- `final/final_qa.json`

## Notes

- The renderer emits inline CSS, inline JS, and inline SVG only.
- The language model never produces HTML directly.
- Token and cost telemetry are best-effort and depend on provider support.
- This remains a pipeline first. The profile CLI is only for selecting and testing providers, not a separate UI layer.
