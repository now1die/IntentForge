# IntentForge Phase 9 final review

Phase 9 adds an opt-in compiler-backed loop summary, arithmetic failure
localization and bounded two-path synthesis. The new profile inherits typed
specifications, deterministic ranking, verified evidence classification and
manual snapshot-based approval.

The four archived layout regressions now preserve their repair category and
sampled repair behavior. Phase 9 recognized all 242 evaluated transformations
with the same sampled candidate effects and categories as their original
layouts. The implementation handles invariant variable steps and up to two
carried scalar locals on a single supported affine loop. The archived nested
Euclidean helper remains outside the model.

The static cohort comparison produced 12/18 exact guided repairs for Phase 9
and 3/18 for Phase 8.5. All configurations had 0/18 code-only exact recall.
There are 18 paired correct controls and two incomplete specifications.
Three faults preserve independently documented, MIT-licensed upstream defects.
The evaluation describes these as adaptations and discloses the absence of
external human review.

## Isolated final results

| Metric | Phase 7.5 | Phase 8.5 | Phase 9 |
| --- | ---: | ---: | ---: |
| Completed original output mismatches on faults | 14/18 | 14/18 | 14/18 |
| Confirmed alerts on correct controls | 0/18 | 0/18 | 0/18 |
| Exact repairs passing holdout | 0/18 | 3/18 | 12/18 |
| Faults with a candidate passing discovery and holdout | 0/18 | 3/18 | 12/18 |

Phase 9's exact holdout rate has a 95% Wilson interval of 43.7% to 83.7%.
All 13 discovery-passing candidates passed holdout and all nine recommended
candidates passed. One behaviorally accepted alternative differed from the
reference tokens. Nine recommendations were shown across 38 cases, with one
ambiguous fault and 29 cases without a recommendation. Three proposals on one
matching control remained optional and collapsed.

The measured gains came from injected faults. Phase 9 detected all three
documented adapted defects and produced a passing repair for zero of them.
It repaired both the localized divisor failure and the int32 overflow. It
abstained on the array bounds failure and the recursive execution limit.
The third carried channel, early exits and data-dependent helper loops also
remain outside the model.

Phase 9 used 31,453 discovery VM steps, 1,867 probe steps and 2,285 candidate
holdout steps. Peak live cells and call depth each reached 32. Exact top-1
and top-3 on the common candidate pool were both 12/18 in static and observed
review order.
[Isolated outcomes](../benchmarks/reports/phase9-live-v1.json)

## Evidence and reproduction

- [Merged baseline and post-merge CI](phase9_baseline.md)
- [Semantic robustness and exact archived diagnoses](phase9_semantic_robustness.md)
- [Static ablations and resource measurements](phase9_generalization_evaluation.md)
- [Candidate precision and holdout validation](phase9_candidate_precision.md) · [Holdout protocol](phase9_holdout_validation.md)
- [Provenance and external defect review](phase9_dataset_provenance.md) · [Leakage audit](phase9_leakage_audit.md)
- [Execution boundary and API compatibility](phase9_security.md)
- [Workbench, snapshots and Chromium captures](phase9_workbench.md)
- [Phase 9.5 readiness](PHASE_9_5_READINESS.md)

The frontend build, historical offline checks and historical isolated worker
replays passed. Live Ollama was unavailable and remains unverified.
