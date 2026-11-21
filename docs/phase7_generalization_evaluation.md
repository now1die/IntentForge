# Generalization evaluation

Run `python -m benchmarks.phase7_evaluate --check` for the static, leakage and metamorphic results. Add `--live` with the documented restricted worker to replay guided policy, same-pool ordering and probe comparisons. Timing is measured separately from deterministic replay equality.

| Static generator | Code-only exact repairs | Test-guided exact repairs | Guided hypotheses on correct controls |
| --- | ---: | ---: | ---: |
| Phase 6 | 0/19 | 0/19 | 0/19 |
| Phase 6.5 | 0/19 | 2/19 | 2/19 |
| Phase 7 layout only | 1/19 | 3/19 | 2/19 |
| Phase 7 helpers only | 0/19 | 3/19 | 3/19 |
| Phase 7 combined | 3/19 | 6/19 | 3/19 |

Against the same Phase 6.5 candidate pool, completed-original gating raised fault alerts from 2/19 speculative alerts to 15/19 confirmed mismatches and lowered correct-control alerts from 2/19 to 0/19. Exact candidate recall stayed at 2/19 in that comparison. The fully combined profile found 6/19 exact candidates, confirmed 15/19 faults, and promoted 3/47 independently tested original/candidate pairs. Its 44 abstentions included three passing repairs whose original hit its call-depth limit. All six exact candidates matched the supplied tests. The original matched in 28 runs and stopped at call depth in four. No correct controls received a confirmed alert.

On the same Phase 7 pool, review ordering moved exact top-1 from 5/19 to 6/19. Exact top-3 stayed at 6/19. Zero of six external faults received an exact repair from examples. Explicit specifications recovered 2/2 in a separate small subset. Natural-language guidance abstained on the one admitted unsupported description. Nine sparse specification cases also ran in observation-only mode. That condition has no expected-output denominator.

The recorded Phase 7 analysis and request latency distributions, Wilson intervals, worker step totals and case-level results are committed as versioned JSON.
