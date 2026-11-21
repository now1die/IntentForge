# Phase 6 generalization evaluation

The audit compared 860 historical sources and references, quarantined two families and left the final cohort intact. The manifest contains 48 cases, with 44 admitted after quarantine. The admitted partitions have 4 development, 4 model-selection, 2 calibration and 34 final cases. The final set contains 16 adjudicable faults, 16 controls and 2 partial specifications. Eight fault/control pairs are adaptations of MIT-licensed upstream algorithms.

| Code-only ablation on the same final cohort | Fault alerts | Correct-control alerts | Exact candidate recall | Top-1 / top-3 |
| --- | ---: | ---: | ---: | ---: |
| Phase 5 | 0/16 | 0/16 | 0/16 | 0/16 |
| Phase 5.5 | 0/16 | 0/16 | 0/16 | 0/16 |
| Semantic analysis with normalized existing generators and new synthesis disabled | 7/16 | 1/16 | 1/16 | 1/16 |
| Phase 6 plus semantic synthesis | 7/16 | 1/16 | 5/16 | 5/16 |
| v4 or pairwise ordering on the identical Phase 6 pool | 7/16 | 1/16 | 5/16 | 5/16 |

Phase 6 recovered 3/8 external-adaptation references and 2/8 internal references. Precision was 7/8 over adjudicable alerts. A correct intermediate-return control alerted, and all 34 cases retained an abstaining recommendation while reviewable candidates could still be offered. The profile made 12 validation attempts and returned 12 compiler-valid alternatives with zero duplicate IDs and two multi-site candidates. The static median was 2.39 ms, with p95 6.83 ms in the recorded run. The report gives Wilson intervals, including 0.142–0.556 for 5/16 exact recall.

The pairwise artifact moved one reference to first on the two selection faults, while deterministic had none first. Both retained the same candidate pool. Its 4 scored selection alternatives came from a single adjudicable candidate-bearing input, and final top ranks tied. Deterministic remains selected because the evidence is too limited for a learned deployment. No model was trained and no probabilities were calibrated.

All 116 robustness transformations preserved supplied observed behavior, alert decisions and candidate categories. Equivalent loop guard restoration was also reproduced on the prior Phase 5.5 orientation miss. The cohort is small and uses project-authored faults and expectations. General recurrence combination, mutual recursion, broad initialization and generalized algorithmic repair remained gaps.

```sh
python -m benchmarks.phase6_audit
python -m benchmarks.phase6_evaluate --check
```

[Leakage audit](../benchmarks/reports/phase6-audit-v1.json) · [Static, ranking, and robustness results](../benchmarks/reports/phase6-static-v1.json)
