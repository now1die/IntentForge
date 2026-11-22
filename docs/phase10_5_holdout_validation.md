# Separation of discovery and holdout

The benchmark sends the frozen discovery examples with comparison enabled. Every candidate that passes discovery is sent back as an independent original with distinct held-out inputs and `compare_candidates=false`. The harness verifies the candidate source identity and expects an empty alternative set on the second response.

All six candidates passed discovery and all six passed holdout. Both suites accepted the three recommended candidates. There were no rejected holdout alternatives or candidate counterexamples in this pool. The pinned external families have three held-out inputs per case and the authored families have two. The archived duplicate lower bound and zero-LCM candidates also passed their original held-out cases and are recorded separately. [Individual holdout observations](../benchmarks/reports/phase105-live-v1.json)
