# Leakage audit

The Phase 7 audit compares frozen source and reference solutions against 935 historical sources from Phases 1–6.5. It checks exact, alpha-normalized and structural similarity, full specifications and expected-vector lists, and shared edit signatures. The historical similarity threshold is 0.94 and the cross-partition threshold is 0.90.

The audit quarantined the integer shelf, lookup weight, unspecified peak and upper inlet families. No cross-partition near match or historical full vector or specification match was found under the audit normalization. One edit signature appeared across admitted partitions. Related variants stay within their family partitions. Development, selection and calibration each have two admitted rows.

The final set admitted 47 of 54 frozen rows. The deterministic policy was recorded before scoring. The initial automorphic reference was supplemented with a three-digit vector during pre-scoring validation because the original tests could not expose that injected mutation. [Audit report](../benchmarks/reports/phase7-audit-v1.json)
