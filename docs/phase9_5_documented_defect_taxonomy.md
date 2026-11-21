# Archived documented defects

| Phase 9 diagnosis | Evidence | Phase 9.5 result |
| --- | --- | --- |
| Lower-end primality lacked an entry guard | Two distinct failing inputs expect false. The adjacent prime at two must retain true. The trial bound uses a nonnegative square. | A pure entry guard matches the archived reference. |
| The fixed-width product omitted the last legal start | When input length equals window width, the original leaves the sentinel unchanged. The nested loop reads the window's fixed cells. | An exact offset edit and an inclusive-bound equivalent fit the diagnostic examples. |
| The missing-member algorithm assumed an origin of zero | Shifted inputs require both endpoints. The defective source has no prepared minimum, and its XOR helper has data-dependent progress. | The projection abstains. |

Phase 9 used single-loop scalar transfer. It lacked a guard insertion rule,
a nested indexed-window model, and the ability to derive a missing range scan.
The historical report includes adapted source, expected vectors, CFG and
reaching definitions. These cases are excluded from independent final scores.
[Archived diagnostic replay](../benchmarks/reports/phase95-static-v1.json)
