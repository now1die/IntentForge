# Leakage audit

The audit checks all 995 indexed historical sources from Phases 1–7. It compares exact and alpha-normalized code, references, near matches, full specifications and vector lists, including holdout lists and cross-mode matches. Similarity thresholds are 0.94 against history and 0.90 across partitions. Related cases remain in one family partition.

The bitflag choice, greater rectangle edge, sequential quarters and sparse interval families were quarantined. The development and calibration partitions therefore have zero admitted rows, the selection partition has two, and the final partition admits 55 of 58. The deterministic ordering and evidence policy were fixed before scoring. The frozen cohort contains 24 admitted faults, 24 controls and seven partially specified cases. [Machine-readable audit](../benchmarks/reports/phase75-audit-v1.json)
