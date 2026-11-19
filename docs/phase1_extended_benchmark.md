# Phase 1.5 extended benchmark

The corpus contains 111 cases. The original 32 remain a historical comparison.
The new 79-case holdout is labeled `AI_ASSISTED_REVIEWED`. Expected sources
and compiler labels were reviewed against the Mini-C subset. Intent
specifications describe manually chosen requirements for these programs.
The holdout is neither an external sample nor a claim about production code.

Categories cover syntax, declarations, references, operators, calls, indexing,
types, conditions, returns, ambiguous intentions, valid-but-wrong logic,
multiple simultaneous errors, valid controls, and unsupported Mini-C. Seven
programs in the full dataset exercise unsupported language features and are
counted separately. All accepted and explicitly rejected references parse and
pass semantic checks. Rejected references encode specific contradictions with
the stated behavior.

## Separation and reproducibility

`python -m benchmarks.review_corpus` verifies schema, unique case IDs,
program-family splits, original and reference validity, and normalized-source
separation from both archived training files and across historical and holdout
evaluation. The near-duplicate screen compares input four-gram Dice similarity
using normalized tokens, a minimum of 20 tokens, and a threshold of 0.88.
It found zero unreviewed pairs involving the published holdout. The check
can miss related control-flow patterns and cannot account for the 160 missing
historical training records. Distinct programs can share a broad error category.

`python -m benchmarks.run --no-ollama --check` compares two complete runs
apart from timing values and verifies report serialization. The [v2 report](../benchmarks/reports/phase1-v2.md)
contains per-category results, and the [JSON](../benchmarks/reports/phase1-v2.json)
contains each candidate, outcome, timing and denominator. The API endpoints
and bundled classifier are reused directly. Rule-only and ML-only are
benchmark adapters around the orchestrator. End-to-end browser review
uses the existing application path.

| Cohort | Rule-only top 1 / top 3 | Existing ML top 1 / top 3 | Hybrid top 1 / top 3 |
|---|---:|---:|---:|
| Phase 1 rerun on 32 historical cases | 9/26 / 9/26 | 10/26 / 10/26 | 10/26 / 10/26 |
| Hardened policy on the same 32 cases | 9/26 / 9/26 | 10/26 / 10/26 | 10/26 / 10/26 |
| New 79-case holdout | 15/62 / 15/62 | 8/62 / 8/62 | 15/62 / 15/62 |
| Combined 111 cases | 24/88 / 24/88 | 18/88 / 18/88 | 25/88 / 25/88 |

All configurations detected all 77 compiler faults and none of the 18
valid-but-wrong logic faults. There were 77/77 correct detections and 77/95
recall overall. The classifier got 11/11 historical labels and 9/17 holdout
labels. Hybrid produced compiler-valid top proposals in 33/42 cases with a
proposal. Of the 88 known-intent cases, hybrid had 25 reference matches,
2 confirmed mismatches, and 61 unknown outcomes. The holdout supports a
narrower conclusion about generalization than the historical split.

## Behavioral observations

Seven holdout cases include a typed finite input/return specification.
The vectors were manually derived from the described requirement. For
example, bulk pricing returns ten for nine units and eight for ten or more.
There is no Mini-C execution facility in the repository. The environment did
not provide an existing isolated Mini-C execution service. No programs ran
for runtime evidence. Finite observations from an injected test double
exercise the correctness, mismatch, timeout, and failure branches without
conferring behavioral evidence on benchmark cases.

The hybrid proposal status across all 111 cases is 94
`BEHAVIOR_UNVERIFIED`, 16 `EXECUTION_UNSUPPORTED` (seven unsupported
language cases and nine proposals failing full compiler checks), and one
`ORACLE_UNAVAILABLE` for a compiler-valid proposal with input/return
vectors. Behavioral success has a zero-observation denominator.
Accepted-source matches and explicitly rejected source matches remain
separate judgments.

A future isolated executor can implement `BehaviorOracle.observe` for the
declared entry and ordered vectors. It must enforce execution deadlines and
resource limits at the boundary, normalize observations into typed values,
and report exit failures separately. Passing a finite vector list supports
only those observed inputs.
