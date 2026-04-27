# ADM Automation Pipeline

This repository implements an automated pipeline for generating Account Development Master (ADM) documents from structured client input.

The target outcome is:

- structured client information in
- publication-ready HTML ADM document out

The implementation is aligned to the assessment materials in:

- [`archive/ADM_Engineer_Assessment.pdf`](archive/ADM_Engineer_Assessment.pdf)
- [`archive/Cisco_ADM.html`](archive/Cisco_ADM.html)

## Assessment Goal

The task is to automate what was previously done with a long manual prompt:

- mirror the benchmark document structure
- preserve numerical rigor
- generate all required sections and tables
- produce a complete HTML artifact rather than raw model prose

This pipeline treats the ADM as a deterministic reporting system, not just a prompt wrapper.

## What This Repo Delivers

- Validation for frozen structured ingress payloads
- Code-computed financials and portfolio facts
- Section-by-section generation across the required 12 ADM sections
- Critique and targeted repair before rendering
- Self-contained HTML rendering with inline CSS, JS, and SVG
- Final HTML QA checks
- CLI-based provider selection and execution flow

## Repository Structure

- [`inputs/clients/northstar-retail.json`](inputs/clients/northstar-retail.json): sample structured client ingress
- [`archive/ADM_Engineer_Assessment.pdf`](archive/ADM_Engineer_Assessment.pdf): assessment brief
- [`archive/Cisco_ADM.html`](archive/Cisco_ADM.html): benchmark reference
- [`config/providers.json`](config/providers.json): named provider profiles
- [`adm_pipeline/`](adm_pipeline): pipeline implementation
- [`tests/`](tests): automated verification

## Pipeline Flow

The execution flow is:

1. Validate ingress
2. Compute facts in code
3. Build section input packets
4. Generate 12 section payloads
5. Run critique and targeted repair
6. Render one HTML report
7. Run final HTML QA

The language model does not generate HTML directly. It generates structured section content only. Financials, validation, critique, and rendering are code-driven.

## Install

```powershell
python -m pip install -e .
```

Optional provider extras:

```powershell
python -m pip install -e .[providers]
```

If you do not want to install the console script, you can run everything from the repo root with:

```powershell
python -m adm_pipeline.cli -d
.\adm.cmd -d
```

## Providers

Supported providers:

- `gemini`
- `openrouter`
- `lmstudio_openai_compat`
- `openai_responses`
- `mock`

The `mock` provider exists for deterministic local verification. Real report generation can be run through Gemini, OpenRouter, or LM Studio.

## Interactive CLI

The main operator entrypoint is:

```powershell
adm -d
```

or from the repo root without install:

```powershell
.\adm.cmd -d
```

The interactive dashboard lets you:

- choose and test a provider
- enter API keys for the current session
- choose the ingress file
- prepare run folders
- run the pipeline
- inspect or prune old runs

## Quick Start

Validate the sample ingress:

```powershell
adm validate inputs/clients/northstar-retail.json
```

Run a deterministic local smoke:

```powershell
adm run inputs/clients/northstar-retail.json --profile mock-local
```

Run a real hosted generation with Gemini:

```powershell
$env:GEMINI_API_KEY="..."
adm run inputs/clients/northstar-retail.json --profile gemini-main
```

Run with LM Studio:

```powershell
adm run inputs/clients/northstar-retail.json --profile lmstudio-local
```

## Run Artifacts

Each run produces:

- `manifest.json`
- `facts.json`
- `section_inputs/secNN.json`
- `sections/secNN.request.json`
- `sections/secNN.raw.json`
- `sections/secNN.normalized.json`
- `critique/global_critique.json`
- `critique/repair_actions.json`
- `critique/benchmark_score.json`
- `final/<client_id>.html`
- `final/final_qa.json`

## Verification

Run the automated test suite:

```powershell
python -m unittest discover -s tests -v
```

The repository includes:

- end-to-end mock pipeline verification
- validation tests
- financial consistency tests
- run cleanup tests
- section normalization tests
- a regression test to ensure fallback text does not leak the Northstar client name into other client outputs

## Notes for Review

- The sample ingress is `northstar-retail.json`.
- The benchmark reference is `archive/Cisco_ADM.html`.
- The repository keeps one representative generated run for review at `runs/northstar-retail/20260427-144500__gemini-main__final-check/`.
- Other generated runs remain git-ignored to avoid committing the full run cache and transient provider artifacts.

## Scope Notes

This implementation is designed to be reusable for any valid `schema_version: "2.0"` client ingress payload, not only the sample Northstar fixture.

Northstar remains the acceptance fixture used to exercise the benchmark workflow and verify the full pipeline.
