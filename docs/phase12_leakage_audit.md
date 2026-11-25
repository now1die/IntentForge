# Leakage audit

Freeze commit `a4d03b0` precedes the final evaluation. Run `python -m benchmarks.phase12_audit`. The audit checks 1,334 historical source specimens through Phase 11.5 for exact, alpha-normalized and high-similarity program and reference overlaps. It checks historical suite reuse, cross-partition overlap and edit shapes, external commit reuse and disjoint discovery and holdout inputs within each case. No case was quarantined.

The jump-search defect shares the broad empty-input theme seen in earlier algorithms. Distinct source, revisions and logic qualify it for this cohort. The automated audit and finite samples leave residual uncertainty about broader family similarity. [Audit report](../benchmarks/reports/phase12-audit-v1.json)
