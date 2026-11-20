# Precision and recall

| Final metric | Phase 5 | Phase 5.5 |
| --- | ---: | ---: |
| Faults alerted | 5/19 | 3/19 |
| Known-correct controls alerted | 3/19 | 2/19 |
| Precision over adjudicable alerts | 5/8 | 3/5 |
| False-negative rate | 14/19 | 16/19 |
| Candidate recall | 3/19 | 2/19 |
| Static top-1 and top-3 | 3/19 | 2/19 |

The tested configuration reduced false alerts and also lost detection and repair recall. Precision did not improve. The gate stays opt-in. The external-adaptation subgroup contributed 0/11 recovered faults. The internal subgroup contributed 2/8. Wilson intervals, separate development ablations and per-category outcomes are in the machine report. The small selected groups limit inference.

[Static report](../benchmarks/reports/phase55-static-v1.json)
