# Phase 10 final review

**PHASE 10 COMPLETE WITH LIMITATIONS**

Phase 10 adds opt-in fixed-array evidence and bounded repair for search intervals, expanding handoffs, range origins and pure helper progress. The isolated final benchmark validated 1/4 adapted documented defects and 5/5 injected faults. The documented repair was behaviorally acceptable on the sampled domain. All five injected repairs matched their exact references. The isolated check reported no confirmed alerts or candidates on thirteen controls.

| Archived diagnostic | Phase 9.5 exact | Phase 10 exact and held-out agreement |
| --- | --- | --- |
| Recursive upper bound | No | Yes |
| Expanding search boundary | No | Yes |
| Shifted missing member | No | No candidate |
| Coprime helper | No | Yes |

The three unrecovered independent defects expose missing saturation semantics, rotated-array neighbor reasoning or a missing LCM domain guard. Independent human review was unavailable. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.

## Verification

- Baseline and post-merge CI for Phase 9.5. [Baseline](phase10_baseline.md)
- Reproduced the applicable historical offline benchmarks and all historical isolated replays, including the isolation enforcement benchmark.
- Passed 825 Python tests with the Clang and restricted-worker paths enabled. The compiler suite passed 220/220 cases, and the keyboard/array verification and stress commands exited successfully.
- Exercised explicit atomic approval, stale-preview invalidation and original runtime classification in Chromium. [Screenshots and workbench coverage](phase10_workbench.md)
- Preserved the private worker contract and disabled public execution. [Security](phase10_security.md)

## Evaluation and implementation

- [Independent upstream results](phase10_external_defect_validation.md) · [Adaptation replay](phase10_adaptation_fidelity.md) · [Provenance](phase10_dataset_provenance.md) · [Leakage audit](phase10_leakage_audit.md)
- [Ablations and performance](phase10_generalization_evaluation.md) · [Precision and ranking](phase10_candidate_precision.md) · [Holdout protocol](phase10_holdout_validation.md)
- [Architecture](phase10_architecture.md) · [Fixed arrays](phase10_fixed_array_semantics.md) · [Index constraints](phase10_index_constraints.md) · [Intervals](phase10_recursive_search.md)
- [Expansion](phase10_expanding_windows.md) · [Origins](phase10_range_origins.md) · [Helpers](phase10_helper_summaries.md) · [Coprime diagnosis](phase10_coprime_analysis.md)
- [Candidate limits](phase10_candidate_generation.md) · [Defect taxonomy](phase10_documented_defect_taxonomy.md) · [Phase 10.5 readiness](PHASE_10_5_READINESS.md)

## Reproduce

```sh
python -m benchmarks.phase10_audit
python -m benchmarks.phase10_upstream --write
python -m benchmarks.phase10_evaluate --check
python -m pytest -q
npm --prefix frontend run build
npm --prefix frontend test
```

With the restricted worker connected, add `--live` to the Phase 10 evaluator and run `npm --prefix frontend test -- phase10.spec.ts`. The benchmark workflow tests source fidelity with a Java compiler and Python. The isolated workflow uses a disposable worker.
