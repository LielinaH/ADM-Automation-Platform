# End-to-End Guide

This document explains the ADM Automation Pipeline from start to finish.

It is intended as the complete working guide for:

- what the system is
- why it was built this way
- how to prepare input
- how to run it
- where the model is used
- what artifacts are produced
- what to review or submit

## 1. Goal

The system automates ADM document generation.

Input:

- one structured client JSON file

Output:

- one publication-ready HTML ADM document

The target benchmark was a Cisco-style sample used locally during development.

The assessment brief was also part of the local working materials used during development.

Those reference materials are not included in the shared repository snapshot.

## 2. What Was Built

This repository is not a single prompt script.

It is a pipeline with these stages:

1. Ingress validation
2. Code-computed facts
3. Section input packet creation
4. Section-by-section model generation
5. Critique and repair
6. Deterministic HTML rendering
7. Final HTML QA

The result is a system that is more controllable and auditable than asking a model to write one giant report in one shot.

## 3. High-Level Architecture

Main folders:

- [`adm_pipeline/`](adm_pipeline): implementation
- [`config/providers.json`](config/providers.json): named provider profiles
- [`inputs/clients/`](inputs/clients): client ingress files
- [`tests/`](tests): automated verification
- [`runs/northstar-retail/20260427-144500__gemini-main__final-check/`](runs/northstar-retail/20260427-144500__gemini-main__final-check): representative generated run kept in repo

Core modules:

- `validation.py`: validates ingress payloads
- `facts.py`: computes all financials and derived facts
- `generation.py`: builds prompts and calls providers
- `sections.py`: normalizes and repairs section payloads
- `critique.py`: checks consistency and benchmark completeness
- `render.py`: renders the HTML artifact
- `html_qa.py`: final rendered artifact checks
- `cli.py`: operator interface

## 4. Why This Methodology Was Chosen

The benchmark asks for:

- structure
- numerical rigor
- consistent formatting
- full report completeness

That is not reliable with one unconstrained model call.

This implementation uses:

- structured ingress as source of truth
- code-computed financials before any generation
- section-by-section generation
- validation and normalization before rendering
- critique before final artifact creation
- deterministic HTML rendering

The design priorities were:

- reliability
- auditability
- recoverability

## 5. Ingress Model

The canonical client input is:

- [`inputs/clients/northstar-retail.json`](inputs/clients/northstar-retail.json)

Expected path for any new client:

```text
inputs/clients/<client-id>.json
```

Required top-level fields:

- `schema_version`
- `client_id`
- `company`
- `narrative_context`
- `annual_adm_spend_usd`
- `business_units`
- `apps`
- `competitors`
- `data_estate`
- `delivery_centers`
- `targets`
- `financial_assumptions`

The ingress is the structured business and transformation brief. It is not just metadata for the model.

## 6. What the LLM Does and Does Not Do

### The LLM does

- section summaries
- executive narrative
- analytical narrative
- benchmark interpretation
- callouts
- section cards and structured prose content

### The LLM does not do

- ingress validation
- financial calculations
- ROI math
- value-stream computation
- deterministic chart values
- HTML layout generation
- final QA

That split is intentional. The model handles interpretation and language. Code handles correctness and artifact production.

## 7. Providers

Supported providers:

- `gemini`
- `openrouter`
- `lmstudio_openai_compat`
- `openai_responses`
- `mock`

Practical state of support in this repo:

- `Gemini`: proven end-to-end
- `OpenRouter`: proven for connectivity and model discovery
- `LM Studio`: usable for local testing, but weaker for benchmark-grade generation
- `mock`: deterministic local verification only

## 8. Interactive CLI

Primary operator entrypoint:

```powershell
adm -d
```

or without install:

```powershell
.\adm.cmd -d
```

The dashboard supports:

- provider selection
- API key entry for the current session
- provider testing
- ingress selection
- folder preparation
- pipeline execution
- run cleanup

## 9. Installation

Install the package:

```powershell
python -m pip install -e .
```

Optional provider extras:

```powershell
python -m pip install -e .[providers]
```

## 10. Typical End-to-End Workflow

### Step 1: Validate the client ingress

```powershell
adm validate inputs/clients/northstar-retail.json
```

### Step 2: Run a deterministic local smoke

```powershell
adm run inputs/clients/northstar-retail.json --profile mock-local
```

### Step 3: Run a real hosted generation

Example with Gemini:

```powershell
$env:GEMINI_API_KEY="..."
adm run inputs/clients/northstar-retail.json --profile gemini-main
```

### Step 4: Review the output

Representative kept output:

- [`runs/northstar-retail/20260427-144500__gemini-main__final-check/final/northstar-retail.html`](runs/northstar-retail/20260427-144500__gemini-main__final-check/final/northstar-retail.html)

## 11. Run Artifacts

Each run produces a working bundle:

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

These artifacts make the run inspectable and auditable.

## 12. Validation, Critique, and QA

### Validation

Checks whether the client JSON matches the frozen schema contract.

### Critique

Checks:

- numeric drift
- contradictions
- missing benchmark structure
- low-quality section output

### Final HTML QA

Checks:

- section anchors
- unresolved placeholders
- external dependency leakage
- empty widgets
- HTML completeness

## 13. Genericity Guardrails

This repo is not intended to work only for Northstar.

The code now includes a regression test ensuring that fallback content does not leak the `Northstar` name into other client outputs.

That matters because the deterministic scaffold is meant to be reusable for any valid client ingress, not hardcoded to one example.

## 14. Current Status

Current engineering status:

- end-to-end pipeline works
- real model generation works
- critique and HTML QA pass
- one representative real run is included in the repo

Current benchmark status:

- strong engineering readiness
- good but not perfect Cisco parity

The main remaining gap is premium visual richness, not pipeline correctness.

## 15. Verification

Run the local test suite:

```powershell
python -m unittest discover -s tests -v
```

The suite covers:

- validation
- financial consistency
- run cleanup
- section normalization and repair
- end-to-end mock execution
- genericity regression

## 16. Security and Repo Hygiene

- local API keys should not be committed
- `.adm.env` is git-ignored
- archive research docs are git-ignored
- generated run cache is git-ignored except for the one representative sample run included for review

If a secret was pasted into chat during development, it should be rotated.

## 17. What to Review

If someone is reviewing the project quickly, the best order is:

1. [`README.md`](README.md)
2. [`END_TO_END_GUIDE.md`](END_TO_END_GUIDE.md)
3. [`inputs/clients/northstar-retail.json`](inputs/clients/northstar-retail.json)
4. [`runs/northstar-retail/20260427-144500__gemini-main__final-check/final/northstar-retail.html`](runs/northstar-retail/20260427-144500__gemini-main__final-check/final/northstar-retail.html)
5. [`adm_pipeline/`](adm_pipeline)

## 18. What to Submit

For an assessment-style submission, the recommended package is:

- GitHub repository
- latest generated HTML artifact
- short note pointing reviewers to:
  - the README
  - this guide
  - the sample ingress
  - the representative final run

## 19. Final Summary

This system converts a structured client brief into a publication-ready ADM HTML artifact through a controlled, testable pipeline.

The key design decision is that the model is used for interpretation and narrative, while code owns financial correctness, structure, rendering, and QA.
