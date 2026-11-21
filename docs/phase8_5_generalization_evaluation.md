# Phase 8.5 generalization evaluation

The final cohort comprises 14 injected faults, 14 paired correct controls and
two partial-specification cases. All baselines used the same final families.
Each guided analysis used the discovery examples from the frozen cohort.

| Static ablation | Exact guided repairs | Compiler-valid emitted candidates |
| --- | ---: | ---: |
| Phase 7.5 | 0/14 | 0/0 |
| Phase 8 | 0/14 | 0/0 |
| Branch analysis added to Phase 8 | 5/14 | 8/8 |
| Coordinated edits added to Phase 8 | 3/14 | 3/3 |
| Loop reasoning added to Phase 8 | 2/14 | 2/2 |
| Combined Phase 8.5 | 10/14 | 13/13 |

All profiles had code-only exact recall of 0/14. The 95% Wilson interval for
Phase 8.5 exact guided recall is 45.4% to 88.3%. The final cohort targets the
new mechanisms and does not estimate prevalence or recall across general
Mini-C programs. Development, selection and calibration rows are reported
separately. Frozen holdout outcomes did not tune the rules or thresholds.

Of 166 transformed comparisons, 162 preserved the candidate categories.
Both loop fault fixtures lost candidates when the comparison operands were
reversed or an unused shadow scope was inserted. The transformed programs
agreed with their originals on the supplied behavioral vectors.

## Archived diagnostics

Exact repairs were generated for the independent-coefficient, upper-branch
arithmetic, Boolean active-window and even-threshold archive cases. The
last had three alternatives and the exact candidate ranked third.
The triad-overlap source encountered a zero divisor on a supplied input.
The coprime-count source uses a data-dependent Euclidean helper. Both
remain beyond these static rules. These archival diagnostics do not enter
the final cohort scores.

## Reproduction

```bash
python -m benchmarks.phase85_audit
python -m benchmarks.phase85_evaluate --check
python -m benchmarks.phase85_evaluate --live --check
```

The last command needs the restricted local Mini-C worker. The reports carry
Wilson intervals, ranks, abstention counts, latency and worker costs.
[Static results](../benchmarks/reports/phase85-static-v1.json) ·
[Isolated results](../benchmarks/reports/phase85-live-v1.json)
