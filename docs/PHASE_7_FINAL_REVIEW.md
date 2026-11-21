# Phase 7 final review

Phase 7 adds opt-in verified mismatch evidence while retaining compiler-valid hypotheses. It restores all six previously lost recursion hypotheses under equivalent source layouts, extends guarded repair to a bounded class of scalar helpers, and improves input-only candidate probe selection inside the existing worker.

On the independent final cohort, Phase 7 confirmed 15/19 faults, gave 0/19 confirmed correct-control alerts and found 6/19 exact candidates with supplied tests. Exact code-only recall was 3/19. Three isolated candidates were promoted for review, and three more passing repairs remained optional after original call-depth stops. This supports further opt-in testing. Broader external algorithm coverage remains limited.

- [Baseline](phase7_baseline.md)
- [Architecture](phase7_architecture.md)
- [Guided evidence and precision](phase7_guided_evidence_policy.md) · [False-positive review](phase7_false_positive_analysis.md)
- [Semantic robustness](phase7_semantic_robustness.md) · [Interprocedural analysis](phase7_interprocedural_reasoning.md)
- [Candidate generation](phase7_candidate_generation.md) · [Probe evaluation](phase7_probe_evaluation.md)
- [Provenance](phase7_dataset_provenance.md) · [Leakage audit](phase7_leakage_audit.md) · [Generalization](phase7_generalization_evaluation.md)
- [Security](phase7_security.md) · [Workbench and screenshots](phase7_workbench.md)
- [Phase 7.5 readiness](PHASE_7_5_READINESS.md)

[Static report](../benchmarks/reports/phase7-static-v1.json) · [Worker verification report](../benchmarks/reports/phase7-live-v1.json) · [Dataset audit](../benchmarks/reports/phase7-audit-v1.json)

## Regression verification

The restricted-profile Python suite passed 744 tests. The compiler regression passed 220/220, keyboard and array verification had zero unexpected outcomes across 65 cases, and the stress harness completed 3,758 cases. Clang 19.1.7 passed its 12-case replay. Historical static benchmarks and the restricted Phase 4.5 through 6.5 live replays reproduced. Local Phase 7 verification used the established worker image with the changed modules mounted read-only under the same runtime restrictions.
