# Phase 11 final review

**PHASE 11 COMPLETE WITH LIMITATIONS**

Public profile 11 adds checked relational evidence, interpolation repair, signed zero-operand helper guards, duplicate-sensitive cyclic tie handling and coordinated range edits. The two archived unused-shadow failures now retain their endpoint candidates. [Architecture](phase11_architecture.md) · [Relational evidence](phase11_relational_evidence.md) · [Structural robustness](phase11_semantic_robustness.md)

| Cohort | Holdout-passing repair | Exact reference |
| --- | ---: | ---: |
| Newly documented upstream adaptations | 2/3 | 1/3 |
| Authored injected faults | 4/4 | 3/4 |
| Archived diagnostic defects | 2/4 | 0/4 |

The fresh upstream outcome matches Phase 10.5 on the same cases. Both upstream successes came from inherited mechanisms. The new rules recovered archived interpolation and coprime behavior. The archived short pivot and shifted missing-member defects remain unresolved. [Documented diagnostic review](phase11_documented_defects.md) · [Independent cohort](phase11_external_validation.md)

All seven candidates compiled and passed fresh holdout. The final interpolation case produced two compatible alternatives. Among ten correct controls there were zero confirmed alerts, zero speculative candidates and zero visible suggestions. Two recommendations passed holdout, and ordering the identical candidate pool preserved exact top-1 and top-3 at 4/7. All 151 final-corpus rewrites preserved the measured signature. [Precision](phase11_candidate_precision.md) · [Holdout](phase11_holdout_validation.md) · [Ablations and costs](phase11_generalization_evaluation.md)

## Verification

The Phase 10.5 merge and all five post-merge workflows were verified. The historical offline and isolated replay matrices completed, as did the compiler fixture, keyboard and array regression, Clang and stress commands. Chromium checks cover atomic approval, checked cyclic evidence, original arithmetic failure and stale-vector invalidation. [Baseline](phase11_baseline.md) · [Workbench screenshots](phase11_workbench.md) · [Security boundary](phase11_security.md)

Pinned Python, JavaScript and Java revisions matched the Mini-C adaptations on 24 family inputs. The audit admitted all final cases. `INDEPENDENT_HUMAN_REVIEW=NOT_AVAILABLE`. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`. [Fidelity](phase11_adaptation_fidelity.md) · [Provenance](phase11_dataset_provenance.md) · [Leakage audit](phase11_leakage_audit.md)

## Implementation details

- [Interpolation](phase11_interpolation_reasoning.md) · [Helper contracts](phase11_helper_contracts.md) · [Cyclic arrays](phase11_cyclic_array_reasoning.md) · [Range and aggregate repairs](phase11_range_aggregate_repairs.md)
- [Candidate limits](phase11_candidate_generation.md) · [Phase 11.5 readiness](PHASE_11_5_READINESS.md)

## Reproduce

```sh
python -m benchmarks.phase11_audit
python -m benchmarks.phase11_upstream --write
python -m benchmarks.phase11_evaluate --check
python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend test
```

Run the evaluator with `--live` against the private worker for fresh holdout. The direct upstream preview requires Python, Node and a Java compiler, and operates independently of the service.
