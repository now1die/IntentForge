# Leakage audit

The freeze was committed before final Phase 10 scoring. The audit checks cases and upstream source hashes, exact and alpha-renamed source, source/reference similarity, executable-example and specification overlap, upstream revision reuse and cross-partition family grouping. Thresholds are 0.94 for historical token similarity and 0.90 across new partitions.

The scan covered 1,243 historical sources. All 28 cases were admitted. Two generic edit shapes recur across partitions, with no source or full metadata overlap at the configured thresholds. Generic edit shape recurrence is reported because the project intentionally studies reusable repair mechanisms. Hash and similarity matches provide bounded evidence about this archive. [Audit result](../benchmarks/reports/phase10-audit-v1.json)
