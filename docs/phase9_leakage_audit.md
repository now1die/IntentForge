# Leakage audit

The audit compares Phase 9 with 1,160 earlier source snapshots and available
specification and test metadata. The check uses exact source normalization,
alpha-normalized shapes and structural near matches. Family partitions are
disjoint. It also checks duplicate expected-output vectors and repeated
specification text across partitions and against earlier corpora.

All 44 frozen records were admitted. The audit detected no historical source
overlap, repeated historical metadata or cross-partition overlap. Two generic
edit-shape templates are shared across partitions. They represent token edit
types, with individual program families and specifications separated.
[Versioned audit](../benchmarks/reports/phase9-audit-v1.json)
