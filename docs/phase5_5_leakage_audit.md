# Phase 5.5 leakage audit

The audit fixes the corpus byte hash, verifies the bundled MIT notice hash, enforces family-exclusive partitions and compares exact and alpha-normalized token representations against 797 historical sources and references. For longer programs it also flags high similarity to historical source. It checks cross-partition token structure, repeated specifications, identical full vector sets and recurring edit templates. Shared edit templates are disclosed because some transfer questions intentionally reuse fault categories.

The audit quarantined seven whole Phase 5.5 families, including a historically similar argument-order example and a selection loop close to a final shape. Three upstream topics already covered by older milestones were excluded at intake. They were binary search, Hamming distance and Armstrong numbers. No exact historical text duplicates or full cross-family specifications or vector sets were admitted. The manifest records the original frozen cases. Scoring uses the admitted cohort, and Phase 5 data remains unchanged.

```sh
python -m benchmarks.phase55_audit
python -m benchmarks.phase55_evaluate --check
```

[Machine-readable audit](../benchmarks/reports/phase55-audit-v1.json)
