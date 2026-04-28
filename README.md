# ADM Automation Pipeline

This repository implements an automated pipeline for generating Account Development Master (ADM) documents from structured client input.

The target outcome is:

- structured client information in
- publication-ready HTML ADM document out

The implementation was developed against an assessment brief and a Cisco-style benchmark artifact that were used locally during development but are not included in the shared repository snapshot.

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
- [`END_TO_END_GUIDE.md`](END_TO_END_GUIDE.md): complete system guide
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

## Methodology

This implementation is intentionally not a single-prompt report generator.

The core methodology is:

- use a frozen structured ingress contract as the source of truth
- compute financials and portfolio facts in code before any model call
- generate the ADM section-by-section instead of asking one model call to write the full document
- validate and normalize section output before it is allowed into the final report
- critique the full report for consistency and completeness before rendering
- render the final artifact deterministically in HTML rather than trusting model-authored markup

This approach was chosen for three reasons:

1. Reliability  
   The assessment requires numerical rigor and stable structure. Code-computed facts are more reliable than asking the model to derive or preserve all financial logic on its own.

2. Recoverability  
   Section-level generation makes retries, repair, and inspection practical. A failed section can be regenerated without re-running the whole report.

3. Auditability  
   Each run preserves the ingress, computed facts, section requests, raw model responses, normalized section payloads, critique output, and final HTML artifact.

## LLM Responsibility Boundary

The LLM is used for:

- executive and analytical narrative
- section summaries
- benchmark interpretation
- callouts, cards, and structured section content

The LLM is not used for:

- ingress validation
- financial math
- ROI computation
- deterministic chart values
- HTML layout generation
- final artifact QA

That split is deliberate. The model handles interpretation and language; the code handles correctness, structure, and artifact production.

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
- The complete working guide is [`END_TO_END_GUIDE.md`](END_TO_END_GUIDE.md).
- The repository keeps one representative generated run for review at `runs/northstar-retail/20260427-144500__gemini-main__final-check/`.
- Other generated runs remain git-ignored to avoid committing the full run cache and transient provider artifacts.

## Scope Notes

This implementation is designed to be reusable for any valid `schema_version: "2.0"` client ingress payload, not only the sample Northstar fixture.

Northstar remains the acceptance fixture used to exercise the benchmark workflow and verify the full pipeline.
