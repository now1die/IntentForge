# Historical overlap and leakage audit

The audit checked 1,124 distinct historical source texts and their available
specification and vector metadata. It compares normalized exact edits,
identifier-normalized shapes and structural near duplicates. Historical
similarity uses 0.94 and cross-partition similarity uses 0.90 for sufficiently
long shapes. It also checks repeated complete specifications and complete
test-vector sets.

All 36 records were admitted. The audit found zero historical overlaps, zero
repeated historical metadata sets and zero cross-partition program overlaps.
Two edit-shape templates cross partitions. Those count reusable token patterns
and are tracked separately from source or family duplication. The hashes and
counts can be reproduced with `python -m benchmarks.phase85_audit`.
[Audit output](../benchmarks/reports/phase85-audit-v1.json)
