# IntentForge Phase 9.5 final review

The opt-in profile adds entry guard insertion, checked finite window
projections, lexical range-origin repair and bounded acyclic helpers with
explicit exit paths. It preserves typed specifications, earlier engine
profiles, compiler gating, isolated verification and manual source approval.

| Isolated result on the new final cohort | Phase 8.5 | Phase 9 | Phase 9.5 |
| --- | ---: | ---: | ---: |
| Exact repairs passing holdout | 0/15 | 2/15 | 9/15 |
| Documented adaptations repaired | 0/5 | 0/5 | 1/5 |
| Injected faults repaired | 0/10 | 2/10 | 8/10 |
| Confirmed completed mismatches | 13/15 | 13/15 | 13/15 |
| Confirmed alerts on correct controls | 0/17 | 0/17 | 0/17 |

Each of 12 compiler-valid Phase 9.5 candidates passed discovery and holdout.
All six recommendations passed. Three non-exact candidates also passed both
suites. The new profile preserved sampled candidate effects across 219
transformations. Upstream replays directly confirmed the Java and JavaScript
adaptations on 39 inputs and no external human adjudication was available.

The archived lower-end primality and final-window specimens received exact
passing repairs. The remaining shifted-origin case and Euclidean coprime
helper remain unsupported. Independent misses also include recursive bounds,
the expanding search window, Gregorian arithmetic and Smith factorization.

The local Python suite passed 817 tests. Historical offline benchmarks,
compiler cases, Clang and isolated replays through Phase 9 passed. Live
Ollama remained unverified.

- [Merged baseline and workflows](phase9_5_baseline.md)
- [Archived defect taxonomy](phase9_5_documented_defect_taxonomy.md)
- [External validation and adaptation fidelity](phase9_5_external_defect_validation.md) · [Fidelity methodology](phase9_5_adaptation_fidelity.md)
- [Ablations and regressions](phase9_5_generalization_evaluation.md) · [Precision and ranking](phase9_5_candidate_precision.md)
- [Holdout protocol](phase9_5_holdout_validation.md) · [Leakage audit](phase9_5_leakage_audit.md)
- [Security and compatibility](phase9_5_security.md) · [Workbench and screenshots](phase9_5_workbench.md)
- [Phase 10 readiness](PHASE_10_READINESS.md)
