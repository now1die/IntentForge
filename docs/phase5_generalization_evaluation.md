# Phase 5 generalization results

The final cohort uses common denominators to attribute changes to candidate generation and review ordering.

| Code-only ablation | Faults alerted | Control false alerts | Candidate recall | Top 1 | Top 3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing v4 | 2/10 | 1/5 | 2/10 | 1/10 | 2/10 |
| v4 pool with structural scan | 6/10 | 2/5 | 2/10 | 1/10 | 2/10 |
| New generation, deterministic ranking | 6/10 | 2/5 | 6/10 | 5/10 | 6/10 |
| v4 gated, v4 pairwise or structural-feature ordering on the new pool | 6/10 | 2/5 | 6/10 | 5/10 | 6/10 |
| Isolated behavior-guided review on the eligible pool | — | — | 6/10 | 6/10 | 6/10 |

Phase 5 code-only precision was 6/8 over adjudicable alerts, with a 2/5 control false-positive rate. All 12 returned proposals were compiler-valid. The evidence policy abstained from formal recommendations on all 16 cases and still exposed possible repairs for review. Compiler-validity and matching examples were measured independently. In the isolated run, 25/28 original and candidate executions were supported, eight candidate results matched supplied examples and four mismatched. The 22,149 total VM steps included 264 probe steps. The 16 cases included one multiple-match result.

Natural-language and explicit requirements recovered 1/1 and 4/4 adjudicable references in their selected subsets. These denominators cover supplied descriptions and expressions and cannot be combined with the code-only cohort. An external generalization result is unavailable. Wilson intervals, per-category detection, evidence location coverage and case-level outcomes are in the report.

The new code-only analysis measured a 2.28 ms median locally. The live run measured a 667 ms median under concurrent local verification load, including the worker start and API round trip. The two reports include mean, median and p95 timings.

```sh
python -m benchmarks.phase5_taxonomy --check
python -m benchmarks.phase5_evaluate --check
python -m benchmarks.phase5_evaluate --live --check
```

[Static evidence and ablations](../benchmarks/reports/phase5-static-v1.json) · [Isolated behavior](../benchmarks/reports/phase5-live-v1.json)
