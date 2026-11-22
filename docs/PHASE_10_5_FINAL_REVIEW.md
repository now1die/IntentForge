# Phase 10.5 final review

**PHASE 10.5 COMPLETE WITH LIMITATIONS**

Opt-in profile 105 adds checked endpoint, adjacent-cell, rotation, zero-guard and aggregate repairs. The final cohort yielded one holdout-passing repair across three documented upstream adaptations, with zero exact source references recovered. Five authored faults yielded five exact holdout-passing repairs. All thirteen correct controls passed with zero confirmed alerts and zero candidate suggestions.

The archived duplicate lower bound and zero-input LCM recovered their exact references and passed held-out verification. The short rotated-array pivot and shifted missing-member repairs remain unsupported. The missing-member digit helper is now projected. The independent upstream coprime zero operand and constant interpolation interval remain unrecovered.

| Evidence | Result |
| --- | --- |
| Pinned before-and-after source fidelity | 24 inputs and 48 revision-specific outcomes agreed |
| Final candidates | 6/6 compiler-valid, discovery-passing and holdout-passing |
| Recommendations | 3/21 with zero recommended holdout failures |
| Confirmed faults | 4/8, with 0/13 confirmed control alerts |
| Same-pool exact ranking | 5/8 top-1 and top-3 both before and after behavioral ordering |
| Metamorphic replay | 131/133 preserved the candidate signature |

`INDEPENDENT_HUMAN_REVIEW=NOT_AVAILABLE`. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.

## Verification

The Phase 10 merge and its five post-merge workflows were verified. Applicable historical offline suites through Phase 10 and historical restricted-worker replays completed. The compiler fixture, keyboard and array regression, Clang and stress commands also completed. The isolated browser scenarios exercise joint approval and stale evidence. [Baseline](phase10_5_baseline.md) · [Workbench screenshots](phase10_5_workbench.md) · [Security boundary](phase10_5_security.md)

## Technical and evaluation material

- [Architecture](phase10_5_architecture.md) · [Endpoint contracts](phase10_5_endpoint_contracts.md) · [Duplicate search](phase10_5_duplicate_search.md) · [Adjacent cells](phase10_5_adjacent_array_reasoning.md) · [Rotation](phase10_5_rotated_array_repair.md)
- [Arithmetic guards](phase10_5_zero_arithmetic_guards.md) · [Ranges](phase10_5_range_aggregate_reasoning.md) · [Helpers](phase10_5_helper_constraints.md) · [Candidate generation](phase10_5_candidate_generation.md) · [Precision](phase10_5_candidate_precision.md)
- [Archived defects](phase10_5_documented_defect_review.md) · [External validation](phase10_5_external_validation.md) · [Fidelity](phase10_5_adaptation_fidelity.md) · [Provenance](phase10_5_dataset_provenance.md) · [Leakage audit](phase10_5_leakage_audit.md)
- [Holdout](phase10_5_holdout_validation.md) · [Generalization and ablations](phase10_5_generalization_evaluation.md) · [Phase 11 readiness](PHASE_11_READINESS.md)

## Reproduce

```sh
python -m benchmarks.phase105_audit
python -m benchmarks.phase105_upstream --write
python -m benchmarks.phase105_evaluate --check
python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend test
```

The upstream replay uses Python, Node and a Java compiler in separate temporary directories. With the private worker running, add `--live` to the evaluator and run `npm --prefix frontend test -- phase105.spec.ts` for new interactive coverage.
