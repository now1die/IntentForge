# IntentForge Phase 1 results

Phase 1 adds a versioned independent Mini-C corpus, compares the existing repair
approaches, audits the packaged classifier, and requires explicit approval for
ambiguous and potentially behavior-changing repairs. The source archive, Mini-C
grammar, and trained model are preserved.

## Independent benchmark

Version 1 has 32 cases, including three valid controls, eight specification-level
faults with valid syntax and semantics, and one unsupported Mini-C program.
The three offline modes detected 20/20 compiler-detectable faults and missed
all eight specification-level faults. Detection precision was 20/20 and recall
across both fault types was 20/28. Both classifying modes predicted 11/11 on
the small class-labeled subset.

| Metric | Rule-based | Existing ML | Hybrid |
|---|---:|---:|---:|
| Exact top proposal | 9/26 | 10/26 | 10/26 |
| Top-1 / top-3 accepted repair | 9/26 / 9/26 | 10/26 / 10/26 | 10/26 / 10/26 |
| Compiler-valid top proposal | 12/12 | 10/10 | 13/13 |
| Confirmed incorrect repair among adjudicated proposals | 1/10 | 0/10 | 1/11 |
| Automatic intended repair | 7/26 | 3/26 | 3/26 |
| Ambiguous cases with automatic abstention | 2/2 | 2/2 | 2/2 |
| Valid-control regressions | 0/3 | 0/3 | 0/3 |

ML recovered the malformed declaration initializer and the array used as a call.
Rules handled the interleaved missing semicolon that ML-only missed. The hybrid
returned a compiler-valid edit to the adjacent return operands which discarded
the second operand, contradicting the specification. It remained a proposal.
Behavioral equivalence beyond accepted reference source was unverified.

Per-category denominators, timing samples, case decisions, and dependency
versions are in the [Markdown report](../benchmarks/reports/phase1-v1.md) and
[JSON report](../benchmarks/reports/phase1-v1.json).

## Verification

| Check | Imported baseline | Phase 1 |
|---|---|---|
| `python -m pytest -q` | 448 passed | 463 passed |
| `python -m test_suite.run_test_cases` | 220 passed | 220 passed |
| `python -m test_suite.run_keyboard_and_array_regression` | 65 exact | 20 exact, 1 syntactically valid while awaiting review, 44 withheld by the safety gate |
| Keyboard/array review-only simulation | Same baseline | 65 exact |
| `python -m test_suite.stress.run_stress_tests .` | 3,758 cases, no exceptions | Same outcome counts, no exceptions |
| `npm --prefix frontend run build` | Passed type checking and build | Passed type checking and build |
| `npm --prefix frontend test` with Chromium and local FastAPI | 8 passed, 5 failed | 14 passed |
| CLI AST and structural correction | Included in imported functionality | Both smoke commands passed |
| Mounted Vercel API | Tested locally | Tested locally, no production deployment |

The old keyboard/array script scores automatic output. All 45 cases on the
current tree that did not match exactly stopped with `correction_requires_review`.
The review-only run preserved the previous candidate and application sequence.
Tests that exercise the historical proposal pipeline now opt into that review
simulation, retaining their existing candidate and validation assertions.
HTTP and browser tests verify that the same proposals require approval in the
actual application. Browser baseline failures concerned backend status text,
unavailable explicit apply controls, and incomplete correction review.
Browser runs used the system Chromium binary. The Vite build reported a large
Monaco chunk. NumPy/Joblib and FastAPI test transport emitted deprecation warnings.

## Ollama verification

The configured `llama3.2:3b` model could not be discovered because the local
service rejected the connection. The benchmark marks Ollama unavailable and
includes no live inference timings or scores. Mocked checks cover model tag
matching, unavailable service, timeout, malformed and empty replies, valid edit
parsing and revalidation, and whether the probe reports latency. The local
verification command can measure inference when the configured service is
reachable. No model was downloaded.

## Model findings and next phase

The historical 640/640 classification score came from a controlled synthetic
split. In the available archive, 588/608 reconstructed test inputs had a
normalized corrupted template seen in training. All 608 corrected templates
were seen in training, and each of the 1,956 populated label-shaped
`strong_pattern` features matched its target. The archive has 3,040 of the
reported 3,200 examples. The independent benchmark shows the gap between a
correct class and a usable repair and leaves open generalization outside Mini-C.

For Phase 2, compare group-held-out baselines and feature ablations, add an
AST- and symbol-aware candidate ranker with explicit abstention, and use
specifications or trusted regression tests as behavioral evidence. The
[generalization analysis](ml_generalization_analysis.md) describes the proposed
evaluation.

## Change inventory

- Added `ai/correction_safety.py`, the benchmark runner and audit, two versioned
  corpus files, JSON and Markdown reports, Phase 1 documentation and Python
  regression tests.
- Updated the orchestrator, correction options, CLI, optional Ollama client and
  probe, FastAPI CORS validation, and dependency metadata.
- Updated the workbench correction review and browser harness, preserved prior
  coverage, and added a live browser test for explicit approval.
- Updated setup, API, ML and correction documentation. Historical verification
  reports and the model artifact remain available.
