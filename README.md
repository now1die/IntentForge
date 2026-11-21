# IntentForge

IntentForge is a Mini-C compiler front end and code-repair workbench. It generates
source-located diagnostics, ASTs and symbol tables, and offers repairs using
compiler rules, a bundled scikit-learn classifier and optional local Ollama.
Phase 1 measures how often these repairs recover a supplied programmer intention.
General detection of specification-level logic errors remains unsupported.

## Run locally

From the repository root with Python 3.12 and Node 20.19 through 24:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell, activate with the
relative path `./.venv/Scripts/Activate.ps1`. Start the frontend in a second terminal:

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open <http://127.0.0.1:5173>. The development frontend calls
`http://127.0.0.1:8000` by default. Set `VITE_API_BASE_URL` at build time to
use another API.

```sh
python main.py --ast examples/valid/demo.mc
python main.py --semantic-errors examples/invalid/semantic_errors.mc
python main.py --correct examples/invalid/broken_if.mc
python main.py --suggest-corrections examples/invalid/missing_semicolon.mc
```

The workbench keeps source in the editor until you select and apply a repair.
`POST /correct` returns safe automatic edits and review metadata for other
proposals. `POST /correction-options` returns ranked choices.
`POST /validate-correction` checks user-written corrections. Compiler validation
covers syntax and supported semantic checks. Behavioral correctness depends on
the intended program.

## Verify Phase 1

```sh
python -m pytest -q
python -m benchmarks.run
python -m benchmarks.audit_training
python -m scripts.verify_ollama
npm --prefix frontend run build
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend test
```

The Ollama probe exits with status 1 if the service, configured model, or a
valid inference result is unavailable. The benchmark keeps that mode optional.
Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to use an installed Chromium binary.
Keep the virtual environment active when running Playwright so it can launch
the backend.

The bundled classifier has 25 classes. Its historical report records 2,560 train
rows and 640 test rows from a controlled synthetic split. The archived source
corpora contain 3,040 rows, so the original 3,200-record run is not fully
reconstructible from the archive. Phase 1 preserves the shipped model and
evaluates a separate frozen corpus.

- [Architecture audit](docs/phase1_architecture_audit.md)
- [Model generalization analysis](docs/ml_generalization_analysis.md)
- [Verification and Phase 1 results](docs/phase1_results.md)
- [Benchmark methodology](benchmarks/README.md)
- [Historical verification](FINAL_VERIFICATION.md)

## Configuration

Ollama is optional. It defaults to `http://127.0.0.1:11434` and
`llama3.2:3b`. Export `OLLAMA_HOST`, `OLLAMA_MODEL`, and `OLLAMA_ENABLED`,
or put them in a root `.env` copied from `.env.example`. Leave Ollama on
loopback or a trusted private network. The application never downloads a model.

Vercel configuration serves the Vite build and mounts the FastAPI app under
`/api`. Set `OLLAMA_ENABLED=false` on a hosted deployment without private
Ollama connectivity. Set `CORS_ALLOWED_ORIGINS` in the API process environment
for a separately hosted frontend. See the [deployment audit](docs/phase1_architecture_audit.md)
and [API documentation](docs/api.md).

## Phase 1.5 verification

The [final review](docs/PHASE_1_FINAL_REVIEW.md) records the 111-case corpus,
safety decisions, hosted CI, and live Ollama status. The
[workbench evidence](audit/phase1-final/README.md) contains fresh screenshots and
reproduction commands. To validate corpus references and reproduce decisions:

```sh
python -m benchmarks.review_corpus
python -m benchmarks.run --no-ollama --check
python -m test_suite.run_keyboard_and_array_regression --verify
```

## Phase 2 intention analysis

Use the **Intention** tab or `POST /v1/intention-analysis` to inspect scoped,
compiler-validated alternatives and supply a return or condition requirement.
Apply any proposed change explicitly. See the [usage guide](docs/phase2_intention_detection.md),
[model card](docs/phase2_model_card.md), [evaluation](docs/phase2_evaluation.md),
and [final review](docs/PHASE_2_FINAL_REVIEW.md).

```sh
python -m benchmarks.phase2_audit
python -m benchmarks.phase2_evaluate --check
```

## Phase 2.5 evaluation and intention modes

The Intention tab exposes code-only, natural-language and explicit
specification analysis. Reports compare these evidence inputs separately.
See the [final review](docs/PHASE_2_5_FINAL_REVIEW.md), [training and data](docs/phase2_5_training.md),
and [mode usage](docs/phase2_5_intention_analysis.md).

```sh
python -m benchmarks.phase25_audit
python -m benchmarks.phase25_evaluate --check
```

## Phase 3.5 evidence and verification

Choose **Intention engine → Phase 3.5 evidence** in Mini-C to try the
new bounded candidate recovery and review guidance. **Inspect compiler
evidence** uses the shared versioned endpoint in Mini-C and C / Clang.
Clang remains opt-in on a supported isolated Linux deployment.

The v4 ranking artifact includes experimental models. The held-out
selection gate kept deterministic ordering active. Live Ollama and
public Clang deployment are unverified. The behavioral oracle is shared by
the Mini-C interpreter and the repair review.

[Phase 3.5 final review](docs/PHASE_3_5_FINAL_REVIEW.md) ·
[Phase 4 readiness](docs/PHASE_4_READINESS.md)

## Mini-C behavioral verification

The bounded Mini-C VM interprets compiler-validated integer and Boolean
programs. The workbench includes recorded evidence and, in a verified local
Linux deployment, an interactive mode for running the current source against
typed tests. It shows per-vector observations, runtime diagnostics and
optional traces. Repairs can be compared with the original, and generated
probe inputs can help distinguish candidates. Expected outputs come from
the reviewer, and every edit requires explicit approval.

The default hosted profile disables interactive execution. C/Clang mode
provides analysis only. Public execution awaits an independent assessment
of the target deployment.

[Local setup](docs/phase4_5_execution_isolation.md) ·
[API reference](docs/phase4_5_interactive_api.md) ·
[Phase 4.5 final review](docs/PHASE_4_5_FINAL_REVIEW.md) ·
[Supported Mini-C](docs/phase4_supported_language.md)

## Phase 5 intention recovery

The Mini-C Intention tab now offers opt-in structural evidence for loop
progress, fixed array boundaries, argument permutations and accumulator
consistency. The review shows the evidence, assumptions and validated edit
spans. In the verified local profile, Phase 5 also supports observational
probes without expected values and an independent behavior-guided review
order once you supply tests. Default engine versions and hosted execution
settings retain their existing behavior.

[Phase 5 review](docs/PHASE_5_FINAL_REVIEW.md) ·
[Frozen evaluation](docs/phase5_generalization_evaluation.md) ·
[Workbench screenshots](docs/phase5_workbench.md)

## Phase 5.5 precision and independent evaluation

Select **Phase 5.5 precision gates** to review supporting evidence alongside
counter-evidence and missing requirements. The gates remain opt-in. On the
frozen cohort they reduced some false alerts and missed additional defects.
The live option uses the same restricted local Mini-C worker and explicit
approval path as Phase 5.

[Phase 5.5 technical review](docs/PHASE_5_5_FINAL_REVIEW.md) ·
[Corpus and provenance](docs/phase5_5_dataset_provenance.md) ·
[Workbench screenshots](docs/phase5_5_workbench.md)

## Phase 6 program reasoning

The opt-in Phase 6 engine adds bounded control-flow, lexical reaching
definitions, return slices and recursion summaries. It can propose
review-only repairs for direct recursive progress, specified base cases and
a narrow class of stale return dependencies. Pure integer comparison
orientation is normalized for loop analysis. Isolated local verification
keeps the existing resource and approval controls.

[Phase 6 review](docs/PHASE_6_FINAL_REVIEW.md) ·
[Evaluation provenance](docs/phase6_dataset_provenance.md) ·
[Workbench screenshots](docs/phase6_workbench.md)

## Phase 6.5 interprocedural reasoning

Select Phase 6.5 in the Mini-C workbench or send `engine_version: 65`
to opt in. The profile adds bounded branch facts, per-path reaching
definitions, call parameter mappings and transitive global effects. It can
propose a one-argument recursive progress edit or compare supported
recurrence operators when expectations are supplied. The same restricted
local worker verifies candidate behavior. Repairs require manual approval.

[Phase 6.5 review](docs/PHASE_6_5_FINAL_REVIEW.md) ·
[Independent evaluation](docs/phase6_5_generalization_evaluation.md) ·
[Workbench screenshots](docs/phase6_5_workbench.md)

## Phase 7 guided repair precision

Opt in to engine 7 in the Mini-C workbench or API. Phase 7 shows
compiler-valid repair hypotheses separately from confirmed mismatches on
supplied tests. It recognizes equivalent guarded recursion layouts and
a bounded set of scalar helper calls. Optional input-only probes can
help distinguish candidate behavior. Local execution retains the existing
isolated worker and every applied edit requires manual approval.

[Phase 7 review](docs/PHASE_7_FINAL_REVIEW.md) ·
[Evaluation](docs/phase7_generalization_evaluation.md) ·
[Workbench screenshots](docs/phase7_workbench.md)

## Phase 7.5 generalized repair recovery

Opt in to engine 75 in the Mini-C workbench or API. It adds bounded
nonunit recursion, repair hypotheses for helper and temporary
dependencies, and quotient/radix recovery. The Phase 7 policy keeps
speculative suggestions separate from verified original mismatches.
Local execution uses the same restricted worker and source edits
require explicit approval.

[Phase 7.5 review](docs/PHASE_7_5_FINAL_REVIEW.md) ·
[Evaluation](docs/phase7_5_generalization_evaluation.md) ·
[Workbench screenshots](docs/phase7_5_workbench.md)

## Phase 8 specification-guided arithmetic

Opt in to engine 8 in the Mini-C workbench or API. Use typed examples and
optional input domains to guide bounded coefficient, predecessor and
scalar dependency repairs. The local worker supplies observed outcomes.
When the original matches all supplied tests, optional suggestions start
collapsed and remain available for manual review.

[Phase 8 review](docs/PHASE_8_FINAL_REVIEW.md) ·
[Holdout validation](docs/phase8_holdout_validation.md) ·
[Workbench screenshots](docs/phase8_workbench.md)

## Phase 8.5 branch-aware repair

Opt in to engine 85 in the Mini-C workbench or API. Trusted examples can guide
conditional arithmetic, integer interval guards, coordinated two-site
coefficient edits, and bounded affine counting repairs. The workbench shows
sampled branch paths, loop counts, and the source locations of coordinated
edits. Local verification and explicit approval use the existing isolated
worker and review flow.

[Phase 8.5 review](docs/PHASE_8_5_FINAL_REVIEW.md) ·
[Holdout validation](docs/phase8_5_holdout_validation.md) ·
[Workbench screenshots](docs/phase8_5_workbench.md)

## Phase 9 semantic robustness

Opt in to engine 9 in Mini-C analysis and local behavioral verification.
It recognizes equivalent loop layouts, summarizes invariant variable
steps and bounded scalar updates, and can propose two coordinated branch
edits. Static arithmetic failure hypotheses use trusted expected outputs.
Observed runtime context comes from the existing isolated worker. Review
and approval remain explicit and tied to the current source snapshot.

[Phase 9 review](docs/PHASE_9_FINAL_REVIEW.md) ·
[Independent defect provenance](docs/phase9_external_defect_review.md) ·
[Workbench captures](docs/phase9_workbench.md)
