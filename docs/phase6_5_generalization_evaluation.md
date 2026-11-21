# Generalization evaluation

Run `python -m benchmarks.phase65_evaluate --check` and, with the documented local worker, `python -m benchmarks.phase65_evaluate --live --check`. The reports include fixed denominators, Wilson intervals, examples, ranking ablations, static and worker latency, and probe cost. Timing is recorded and excluded from replay equality.

| Final profile | Exact reference | Fault alerts | Correct-control alerts | Static top 1 |
| --- | ---: | ---: | ---: | ---: |
| Phase 5 | 0/6 | 0/6 | 0/13 | 0/6 |
| Phase 5.5 | 0/6 | 0/6 | 0/13 | 0/6 |
| Phase 6 | 0/6 | 0/6 | 1/13 | 0/6 |
| Paths only | 0/6 | 0/6 | 1/13 | 0/6 |
| Recursion only | 3/6 | 3/6 | 1/13 | 3/6 |
| Precision only | 0/6 | 0/6 | 0/13 | 0/6 |
| Guided recurrence component | 1/6 | 1/6 | 3/13 | 0/6 |
| Combined code-only | 3/6 | 3/6 | 0/13 | 3/6 |
| Combined guided | 5/6 | 5/6 | 4/13 | 4/6 |

The 20th case has an ambiguous specification and is excluded from fault and correct-control denominators. Code-only fault-detection precision was 3/3 alerts. Guided precision was 5/9 alerts. External-adaptation recall was 1/2 with or without supplied examples. The helper-mediated Sylvester fault remained unresolved.

On the identical admitted worker candidate pool, behavioral review moved exact top-1 from 4/6 to 5/6. Top-3 stayed at 5/6. The code-only pool held a single alternative per detected case. The learned comparisons use the same candidate IDs as their static baselines. With a quarantined selection partition and a small final cohort, deterministic static ranking remains selected.
