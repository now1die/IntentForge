# Phase 6.5 final review

Phase 6.5 adds bounded return-path and interprocedural evidence, multi-parameter recursion repair, test-guided recurrence alternatives and stricter intermediate-return precision. It keeps deterministic static ranking and uses the existing isolated worker for observed behavior. Users opt in to engine 65 and approve each applied edit.

The final evaluation admitted 20 programs, including six injected faults, thirteen correct controls and one ambiguous specification. It found 3/6 exact repairs code-only and 5/6 with supplied tests. Correct-control alerts were 0/13 code-only and 4/13 with supplied tests. Isolated verification confirmed five exact repairs on the supplied vectors. The small cohort and quarantined selection cases limit broader generalization claims.

- [Baseline and post-merge workflows](phase6_5_baseline.md)
- [Architecture](phase6_5_architecture.md)
- [Path sensitivity](phase6_5_path_sensitivity.md)
- [Interprocedural summaries](phase6_5_interprocedural_analysis.md)
- [Multi-parameter recursion](phase6_5_multi_parameter_recursion.md)
- [Recurrence repair](phase6_5_recurrence_repair.md)
- [Return precision](phase6_5_return_precision.md)
- [Candidate generation](phase6_5_candidate_generation.md)
- [Behavioral verification](phase6_5_behavioral_verification.md)
- [Dataset provenance](phase6_5_dataset_provenance.md)
- [Leakage audit](phase6_5_leakage_audit.md)
- [Evaluation and ablations](phase6_5_generalization_evaluation.md)
- [Security and deployment](phase6_5_security.md)
- [Workbench and screenshots](phase6_5_workbench.md)
- [Phase 7 readiness](PHASE_7_READINESS.md)

Reproducible results are in the [static](../benchmarks/reports/phase65-static-v1.json), [live](../benchmarks/reports/phase65-live-v1.json), and [audit](../benchmarks/reports/phase65-audit-v1.json) reports. Historical reports remain versioned separately.
