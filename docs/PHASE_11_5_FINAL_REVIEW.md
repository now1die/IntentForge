# Phase 11.5 final review

**PHASE 11.5 COMPLETE WITH LIMITATIONS**

**Repair research: COMPLETE WITH LIMITATIONS.** Phase 11.5 adds concrete endpoint recognition, first-minimum cyclic seam repair, and a checked two-site range seed and origin repair. It preserves the previous shadow fixes and surfaces ambiguous interpolation alternatives through isolated probes. [Architecture](phase11_5_architecture.md) · [Endpoint contracts](phase11_5_optional_endpoints.md) · [Cyclic reasoning](phase11_5_duplicate_cyclic_reasoning.md) · [Range dependencies](phase11_5_shifted_range_dependencies.md)

| Cohort | Passed independent holdout | Exact reference |
| --- | ---: | ---: |
| Fresh documented upstream defects | 0/3 | 0/3 |
| Project-injected faults | 3/3 | 3/3 |
| Archived diagnostic faults | 2/4 | 1/4 |

The new rules recovered the archived explicit-bound exponential fault exactly. Both interpolation patches passed its archived holdout and remain ambiguous. The short-rotation and missing-member implementations remain unsupported by the new grammar. Fresh upstream results matched Phase 11 on the same cases. Discovery produced a misleading inherited offset repair for the empty retained run and fresh holdout rejected it. The other two documented defects were unrecovered. [Independent evaluation](phase11_5_external_validation.md) · [Interpolation](phase11_5_interpolation_disambiguation.md) · [Holdout](phase11_5_holdout_validation.md)

The ten compiled candidates had seven discovery passes and six holdout passes. The only recommendation passed. Confirmed control alerts were 0/9. One correct control had three collapsed inherited suggestions. All 131 final metamorphic variants preserved the measured candidate signature. [Precision](phase11_5_candidate_precision.md) · [Ablations](phase11_5_generalization_evaluation.md) · [Robustness](phase11_5_semantic_robustness.md)

**Product stabilization: COMPLETE WITH LIMITATIONS.** Verified local development and built preview, exact simulated forwarded hosts, same-origin analysis, startup diagnostics, and browser fallbacks for both a blocked entry script and a failed application chunk. Actual Codespaces access returned HTTP 403. The reported hosted HTTP/2 asset failure remains unverified. [Setup guide](phase11_5_codespaces_setup.md) · [Diagnostics](phase11_5_developer_diagnostics.md) · [Workbench captures](phase11_5_workbench.md)

All five Phase 11 post-merge workflows were verified. The historical offline and restricted-worker replays completed. External raw and Mini-C outcomes agreed on 24 distinct inputs. `INDEPENDENT_HUMAN_REVIEW=NOT_AVAILABLE`. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`. [Baseline](phase11_5_baseline.md) · [Provenance](phase11_5_dataset_provenance.md) · [Leakage audit](phase11_5_leakage_audit.md) · [Security](phase11_5_security.md) · [Phase 12 readiness](PHASE_12_READINESS.md)

## Reproduce

```sh
python -m benchmarks.phase115_audit
python -m benchmarks.phase115_upstream --write
python -m benchmarks.phase115_evaluate --check
python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend test
python -m scripts.doctor
```

Use `--live` with the existing private worker for a fresh holdout replay. The upstream replay uses Python, Node and a Java compiler independently of the application.
