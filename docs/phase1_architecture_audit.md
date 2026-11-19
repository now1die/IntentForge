# Phase 1 architecture audit

The original archive was imported on `phase-1-intention-benchmarking`. The
baseline was 448 passing Python tests. The bundled model is preserved byte for
byte. The [Phase 1 results](phase1_results.md) records the suite comparisons.

| Layer | Active path | Current capability |
|---|---|---|
| Lexer and parser | `compiler/lexer.py`, `compiler/parser.py`, `compiler/error_recovery.py` | PLY tokenization, Mini-C grammar, source-located AST and recovery diagnostics |
| Semantic analysis | `compiler/semantic_analyzer.py`, `compiler/symbol_table.py` | Scope, types, function calls, arrays, return and flow diagnostics |
| Native repair | `compiler/correction.py`, `compiler/compound_recovery.py` | Candidate edits, application to temporary source, target and progress validation |
| ML data and training | `main.py`, `ai/dataset_generator.py`, `ai/scenario_training.py`, `ai/error_predictor.py` | Synthetic training families, stratified split, dictionary vectorizer and logistic regression |
| Prediction and ranking | `ai/error_context.py`, `ai/feature_extraction.py`, `ai/error_predictor.py`, `ai/ml_candidate_generator.py`, `ai/candidate_ranker.py` | Class prediction from parser-derived context, class-conditioned edits, ML-based ranking |
| Correction decisions | `ai/correction_orchestrator.py`, `ai/correction_safety.py`, `ai/correction_options.py` | Iterative validation, ambiguity detection, review gating and interactive alternatives |
| Optional local inference | `ai/llm_fallback.py`, `scripts/verify_ollama.py` | Model discovery, structured edit or selection, interactive review and generation, compiler validation |
| Transport | `backend/app/main.py`, `backend/app/routes/*`, `backend/app/dependencies.py`, `api/index.py` | FastAPI schemas, cached model, analysis and correction routes, mounted Vercel entrypoint |
| UI | `frontend/src/App.tsx`, `frontend/src/services/api.ts`, `frontend/src/components/CorrectionPanel.tsx` | Vite and React workbench, Monaco editing, diagnostic and correction review, explicit apply |
| Independent evaluation | `benchmarks/` | Frozen cases, comparison modes, raw and aggregated observations, reproducible offline scoring |

The CLI enters through `main.py`. Browser correction requests call `/correct`,
`/analyze`, and `/correction-options` in parallel. Analysis of the original
source keeps markers aligned. The two correction endpoints serve different
purposes. The orchestrator iterates through validated edits, and the options
path presents alternatives for explicit selection. `/validate-correction`
checks complete user-written source.

The safety policy uses validation and edit structure. A unique validated
localized delimiter insertion can be eligible for automatic correction.
Detected competing repairs, operator and binding changes, whole-source
alternatives and unverified edits require review. Safety metadata augments
existing source spans, diagnostics, validation and candidate explanations.
The automatic correction response retains the reviewed proposal under
`history[].validation.corrected_source`. A review-only simulation is available
to the Python verification tests to preserve coverage of the previous ranking
and iteration behavior.

## Deployment

Python 3.12 and the pinned scikit-learn 1.8.0 and Joblib 1.5.2 versions are shared
by local and Vercel config. The bundled Joblib artifact is trusted repository
data. Loading starts on demand and is cached. Missing or unreadable models cause
`503` on correction endpoints. The anatomy of a program remains available via
analysis. The health route reports model and optional Ollama readiness.
Bad request payloads produce `422`. Unexpected errors return a generic `500`.

Local Uvicorn uses port 8000 and the Vite dev server uses 5173. CORS supports the
local Vite origins and explicit additional HTTP(S) origins. The root `.env`
is read by the Ollama adapter. CORS uses the API process environment. The
`VITE_API_BASE_URL` build-time variable selects a split-host API. For the
checked-in Vercel configuration, Vite serves static output and `api/index.py`
mounts the same app under `/api`.

Ollama discovery checks the requested tag. Unavailable services and malformed
replies are handled by the optional fallback. Set `OLLAMA_ENABLED=false` where
no private Ollama instance is reachable. The deployed server cannot reach a
developer machine's loopback. The mounted entrypoint was tested locally. No
production deployment was performed.

The compiler implements a documented Mini-C subset. It does not execute programs
or establish behavioral equivalence. Static semantic analysis detects language
violations. Specifications, test oracles and general inference of a programmer's
intended behavior are future capabilities.
