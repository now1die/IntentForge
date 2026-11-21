# Phase 7.5 final review

Phase 7.5 adds opt-in generalized synthesis for bounded recursive steps, local recurrence terms, helper argument dependencies and related loop radices. It keeps the Phase 7 evidence policy, isolated verification and manual approval. Both archived helper shadow-scope failures recovered their hypotheses.

The new final cohort admits 24 faults, 24 controls and seven partial specifications. Phase 7.5 recovered 16/24 exact guided repairs, including four of six new external adaptations. All sixteen exact candidates passed separate held-out tests. Confirmed mismatch recall stayed at 23/24 with zero confirmed alerts on controls. Seven correct controls had speculative suggestions. Code-only recovery remained limited to 1/24.

- [Baseline and original CI](phase7_5_baseline.md)
- [External failure taxonomy](phase7_5_external_failure_taxonomy.md) · [Architecture](phase7_5_architecture.md)
- [Nonunit recursion](phase7_5_nonunit_recursion.md) · [Interprocedural repairs](phase7_5_interprocedural_repairs.md)
- [Shadow-scope robustness](phase7_5_shadow_scope_robustness.md) · [Candidate generation](phase7_5_candidate_generation.md)
- [Behavioral verification](phase7_5_behavioral_verification.md) · [Generalization](phase7_5_generalization_evaluation.md)
- [Dataset provenance](phase7_5_dataset_provenance.md) · [Leakage audit](phase7_5_leakage_audit.md)
- [Security](phase7_5_security.md) · [Workbench and screenshots](phase7_5_workbench.md)
- [Phase 8 readiness](PHASE_8_READINESS.md)

[Static results](../benchmarks/reports/phase75-static-v1.json) · [Live and holdout results](../benchmarks/reports/phase75-live-v1.json) · [Audit report](../benchmarks/reports/phase75-audit-v1.json)

## Regression verification

The local restricted-profile Python suite passed 759 tests. The compiler passed 220/220 cases, keyboard and array verification recorded zero unexpected outcomes across 65 cases, and the stress harness completed 3,758 cases. Clang 19.1.7 passed its 12-case replay. Local isolated checks used the existing Linux worker image with read-only mounts of the current Python modules. The CI workflow builds the worker from the repository Dockerfile.
