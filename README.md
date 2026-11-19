# AI-Assisted Syntax Error Detection and Correction Compiler

This repository contains **Phases 1 through 9** of a Mini-C compiler
front-end: a PLY Lex lexer, an explicitly defined PLY Yacc grammar, source-located
AST construction and visualization, structured lexical/syntax diagnostics,
examples, tests, traditional syntax recovery, source correction candidates, and
model-independent AI context interfaces, a scoped symbol table, and basic semantic
analysis, validated synthetic ML data generation, explainable compiler-context
features, a Scikit-learn correction classifier, iterative compiler-validated
automatic correction, a constrained local Ollama fallback for unresolved errors, and a
FastAPI backend with a React, TypeScript, Vite, and Monaco compiler workbench.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\python main.py --tokens examples\valid\demo.mc
.\.venv\Scripts\python main.py --ast examples\valid\demo.mc
.\.venv\Scripts\python main.py --tokens examples\invalid\lexical_errors.mc
.\.venv\Scripts\python main.py --errors examples\invalid\multiple_errors.mc
.\.venv\Scripts\python main.py --error-context examples\invalid\broken_if.mc
.\.venv\Scripts\python main.py --symbols examples\valid\scopes_and_functions.mc
.\.venv\Scripts\python main.py --semantic-errors examples\invalid\semantic_errors.mc
.\.venv\Scripts\python main.py --generate-dataset
.\.venv\Scripts\python main.py --train-model
.\.venv\Scripts\python main.py --predict-error examples\invalid\broken_if.mc
.\.venv\Scripts\python main.py --correct examples\invalid\broken_if.mc
.\.venv\Scripts\python main.py --suggest-corrections examples\invalid\missing_semicolon.mc
.\.venv\Scripts\python main.py --correct --auto-apply-threshold 0.30 --llm-fallback-threshold 0.20 examples\invalid\multiple_errors.mc
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload
.\.venv\Scripts\python -m pytest
```

In a second terminal, start the Phase 9 workbench:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The frontend expects the API at
`http://127.0.0.1:8000` by default. See `frontend/.env.example` to override it.

With no mode flag, the CLI defaults to token output for backward compatibility.
See `docs/mini_c_spec.md` for the language definition and `docs/grammar.md` for the
CFG and precedence table.
Recovery design and candidate semantics are documented in
`docs/error_recovery.md`.
Scope and type rules are documented in `docs/semantic_analysis.md`.
The dataset, feature, training, and prediction design is documented in
`docs/ml_correction.md`. The bundled ML-first model has 21 correction classes and
2,400 compiler-validated synthetic training records. The unresolved-error fallback
uses a local Ollama model; no cloud API key is required. Reproduced scenario coverage and
current results are in `test_suite/ML_FIRST_FULL_SCENARIO_VERIFICATION.md`.

To run the complete local verification suite from PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe test_suite\run_test_cases.py
.\.venv\Scripts\python.exe test_suite\run_keyboard_and_array_regression.py
.\.venv\Scripts\python.exe test_suite\stress\run_stress_tests.py .
```
The Phase 6 ranking, confidence, validation, and iteration policy is documented
in `docs/automatic_correction.md`.
The optional structured local Ollama fallback is documented in `docs/llm_fallback.md`.
The FastAPI endpoints, schemas, error policy, and local run instructions are in
`docs/api.md`.
The Phase 9 UI architecture, compiler-logic boundary, and verification commands
are documented in `docs/frontend.md`.

## Vercel deployment

Deploy the repository root as one Vercel project. The Vite workbench is built as
static output and the existing FastAPI application is mounted under `/api` by
`api/index.py`. Production browser requests therefore stay on the deployment's
own origin.

Configure these environment variables for a local deployment:

- `OLLAMA_HOST` — local Ollama endpoint, default `http://127.0.0.1:11434`.
- `OLLAMA_MODEL` — installed local model, default `llama3.2:3b`.
- `CORS_ALLOWED_ORIGINS` — optional comma-separated exact frontend origins.

There is no `GROQ_API_KEY` requirement in the active local correction pipeline.
Local `.env` and `.env.*` files are ignored; committed `.env.example` files contain
names and safe defaults only. The deployment uses Python 3.12 so the pinned
Scikit-learn and Joblib versions match the deployment classifier artifact.

## Interactive correction choices

The workbench now supports user-controlled correction review. Clicking **Correct** generates multiple compiler-validated alternatives ranked with the trained ML classifier, rather than silently applying one repair. Users can select an option and apply it, open the custom correction editor, or edit the original source themselves. Custom corrections are sent to `/validate-correction` before application.

New API endpoints:
- `POST /correction-options` — returns ranked, compiler-validated alternatives for the first repairable diagnostic.
- `POST /validate-correction` — validates a user-selected or custom corrected source before it is applied.
