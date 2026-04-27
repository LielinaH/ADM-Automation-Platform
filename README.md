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

- `openai_responses`
- `lmstudio_openai_compat`
- `openrouter`
- `mock` for deterministic local smoke tests

The benchmark default is hosted OpenAI. The `mock` provider exists for local verification and CI-like runs without network access.

## Install

```powershell
python -m pip install -e .
```

Optional provider dependencies:

```powershell
python -m pip install -e .[providers]
```

## Example Commands

Validate ingress:

```powershell
adm validate inputs/clients/northstar-retail.json
```

Run the full local deterministic pipeline:

```powershell
adm run inputs/clients/northstar-retail.json --provider mock --run-dir runs/northstar-retail/local-smoke
```

Run generation only:

```powershell
adm generate inputs/clients/northstar-retail.json --provider mock --run-dir runs/northstar-retail/local-smoke
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
