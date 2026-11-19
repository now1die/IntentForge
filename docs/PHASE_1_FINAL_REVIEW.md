# IntentForge Phase 1 final review

**Assessment: PHASE 1 COMPLETE WITH LIMITATIONS**

Phase 1.5 expanded the independent evaluation, made delimiter repair policy
more conservative, and added reproducible checks for the compiler, workbench
and benchmark. The foundation is ready for further intention-ranking research.
Live Ollama and execution-backed behavioral validation remain unverified.

The work branched from [`fae9fa43a5805f1c6e4125621ef9f7a46e4e1f92`](https://github.com/now1die/IntentForge/commit/fae9fa43a5805f1c6e4125621ef9f7a46e4e1f92).
The original compiler, model, source archive, and historical v1 corpus are
preserved. There were no public FastAPI or frontend contract changes.
The exact change inventory is in the
[branch comparison](https://github.com/now1die/IntentForge/compare/phase-1-intention-benchmarking...phase-1-reliability-hardening).

## Evaluation and intention detection

The benchmark now has 111 cases, comprising 32 frozen historical cases and
79 new AI-assisted and reviewed holdout cases. Corpus review checked
normalized training and cross-split overlaps, near duplicates, compiler
validity, and accepted and rejected references. The shipped model was
never retrained or tuned against these cases.

| Scope | Rule-based top 1 | Existing ML top 1 | Hybrid top 1 |
|---|---:|---:|---:|
| Reproduced Phase 1 baseline, 32 cases | 9/26 | 10/26 | 10/26 |
| Hardened policy on historical cases | 9/26 | 10/26 | 10/26 |
| New holdout only | 15/62 | 8/62 | 15/62 |
| Combined corpus | 24/88 | 18/88 | 25/88 |

Top-3 matched top-1 here. The classifier dropped from 11/11 on historical
labels to 9/17 on holdout labels. Compiler detections had 77/77 precision,
with no false positives on the nine valid controls. Overall detection
recall was 77/95. All 18 specification-level faults passed the compiler
undetected. Hybrid top proposals passed compiler checks in 33 of 42 cases
with a proposal. It produced 25 known-intent matches, two confirmed
reference mismatches, and 61 unknown outcomes on 88 cases with known
intent. Candidate generation and ranking for new program families
remain limited. General intent detection is unsupported.

Run `python -m benchmarks.run --no-ollama` for the expanded dataset and
`python -m benchmarks.run --no-ollama --check` for a reproducibility check.
See the [extended benchmark](phase1_extended_benchmark.md),
[raw results](../benchmarks/reports/phase1-v2.json), and the earlier
[training leakage analysis](ml_generalization_analysis.md).

## Behavioral verification

Seven cases have typed input and expected-return vectors. No Mini-C
execution engine or existing isolated executor was available, so no
benchmark program was executed. The reusable oracle interface records
verified, mismatch, unverified, unavailable and unsupported states.
Oracle unit tests adjudicate fixed observations from a test double,
including behavior-changing and compiler-valid sources, timeout and
failure. These tests establish the evaluation contract, with zero
runtime observations in the benchmark. Runtime false-safe and
false-risky rates remain unmeasured.

## Safety and workbench

Token-level checks now catch misleading standalone delimiters, for-header
statement boundaries, potential expression regrouping, and uncertain scope
closures. The unchanged candidate history and approval workflow still lets
users review and edit those proposals.

On the same 111 inputs, the hybrid policy went from 12 to 11 automatically
edited cases and from 24 to 26 requiring review. Ambiguous abstention
improved from 6/7 to 7/7. The withheld automatic edit would have placed a
return inside an ambiguous loop. The workbench still exposed accepted
reference proposals in 28/88 cases. See the
[policy audit](correction_safety_audit.md) for the guardrails and denominators.

## Ollama

`LIVE_OLLAMA_STATUS=NOT_VERIFIED`. Discovery for `llama3.2:3b` at the
configured loopback endpoint failed with connection refused. No live model
outputs, inference latencies, or accepted candidates were recorded.
Mocked verification passed. The live benchmark probe reports only
observed responses and creates an output file only if a response arrives.
See the [verification procedure](ollama_live_verification.md).

## Regression and CI

| Check | Phase 1 baseline | Phase 1.5 |
|---|---:|---:|
| Python tests | 463 passed, 0 failed | 477 passed, 0 failed |
| Compiler suite | 220 passed, 0 failed | 220 passed, 0 failed |
| Keyboard/array fixture cases | 20 exact, 45 review stops | 20 exact, 45 expected references available for review, 0 lost, 0 crashes |
| Stress cases | 3,758, no crashes | 3,758, no crashes or phase mismatches |
| Browser regressions | 14 passed, 0 failed | 14 passed, 0 failed |
| TypeScript and production build | Passed | Passed |
| Benchmark consistency | v1 reproduced | Full v2 checked across two runs |
| Workbench evidence capture | Historical only | 1 capture run, 9 fresh PNGs |

The first baseline Python run had nine failing mocked Ollama tests when
the entire suite was launched with `OLLAMA_ENABLED=false`. That environment
override disables the mocked service before those tests can call it.
The clean baseline rerun reproduced 463/463. Standard CI omits the
global override. The legacy keyboard report's `failed` field still
counts 44 syntax-invalid outputs awaiting review. The new strict
verification evaluates whether the expected proposal remains available.

GitHub ran and passed [Python tests](https://github.com/now1die/IntentForge/actions/runs/44550286269),
[Frontend tests](https://github.com/now1die/IntentForge/actions/runs/44550286208),
and [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44550286231)
at implementation commit `878b3e09e41f0657492fd17d8dc549b51653b8ea`.
These workflows run on pushes and pull requests. The optional live
Ollama job was skipped on the hosted runner. The CI jobs have read-only
repository permissions and pin official actions by SHA. No production
deployment was performed.

## Screenshot evidence

The [evidence index](../audit/phase1-final/README.md) links the main workbench,
safe and review-required corrections, ambiguity, before/after preview, syntax
and semantic diagnostics, and both viewport sizes. PNGs came from the real
local FastAPI and Vite application. No requests were mocked in capture.
The interface layout is the existing workbench.

## Phase 2 readiness

The benchmark, reference review, safety decisions, and continuous checks
provide a reproducible starting point. Before training a new ranker,
collect genuinely independent programs and diversify the case families.
An execution engine would enable bounded behavioral observations.
A new ranker should keep an abstention path and be evaluated on both
accepted and explicitly rejected behaviors. The current benchmark and
the original model leave arbitrary valid-but-wrong logic unresolved.
