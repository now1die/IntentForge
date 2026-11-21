# Phase 8 final review

Engine 8 adds typed requirements, bounded arithmetic hypotheses and optional repair presentation with the same Phase 7 verified-original policy. It synthesizes nearby coefficient, predecessor, operator and local-return edits using compiler and lexical evidence. It retains the isolated worker and manual approval.

On the new frozen cohort, exact guided repairs rose from 0/23 with Phase 7.5 to 19/23. All 19 passed independent held-out tests. Eight new external fault adaptations received exact repairs, and one non-exact candidate also passed both suites. Two discovery-passing alternatives failed holdout and had received no recommendation. Code-only recall stayed at zero, confirmed detection remained 22/23, and correct-control confirmed alerts remained zero. The archived same-pool presentation check reduced initially visible suggestions from 17 to zero while preserving candidate identities.

- [Baseline and merge CI](phase8_baseline.md) · [Architecture](phase8_architecture.md)
- [Specifications](phase8_specification_model.md) · [Constraints](phase8_constraint_generation.md)
- [Arithmetic synthesis](phase8_arithmetic_synthesis.md) · [Closed forms](phase8_closed_form_repairs.md) · [Predecessor factors](phase8_predecessor_repairs.md)
- [Interprocedural repairs](phase8_interprocedural_repairs.md) · [Precision and review burden](phase8_candidate_precision.md)
- [Holdout validation](phase8_holdout_validation.md) · [Provenance](phase8_dataset_provenance.md) · [Leakage audit](phase8_leakage_audit.md)
- [Generalization and ablations](phase8_generalization_evaluation.md) · [Security](phase8_security.md) · [Workbench screenshots](phase8_workbench.md)
- [Phase 8.5 readiness](PHASE_8_5_READINESS.md)

[Static report](../benchmarks/reports/phase8-static-v1.json) · [Live and holdout report](../benchmarks/reports/phase8-live-v1.json) · [Audit report](../benchmarks/reports/phase8-audit-v1.json)

## Regression verification

The restricted-profile local suite passed 775 Python tests. The compiler passed 220/220 cases, keyboard and array verification found zero unexpected outcomes across 65 cases, and the stress harness completed 3,758 cases. Clang 19.1.7 passed its 12-case replay. Local isolated verification used the existing Linux worker image with current Python modules mounted read-only. The GitHub workflow builds the worker from the repository Dockerfile.
