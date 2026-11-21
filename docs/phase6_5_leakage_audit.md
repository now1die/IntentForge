# Leakage audit

Run `python -m benchmarks.phase65_audit`. The audit verifies the freeze and upstream hashes, compares source and reference code to 908 historical sources, and checks full specifications, full test lists and shared source edit shapes. It uses exact repair keys, alpha-normalized token shapes and near-match ratios of 0.94 within history and 0.90 across new partitions.

| Partition | Frozen | Admitted |
| --- | ---: | ---: |
| Development | 3 | 1 |
| Model selection | 2 | 0 |
| Calibration | 1 | 1 |
| Final | 22 | 20 |

Double factorial overlapped historical code. Indexed weight and signed tree overlapped final-family shapes and were quarantined. No full historical specification or vector list matched under the audit normalization. The admitted partitions share zero measured edit shapes. Similar source shapes and related controls within final remain correlated. The final rows are therefore also described by family and provenance. Deterministic ordering was fixed before scoring.
