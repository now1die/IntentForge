# Phase 12 final review

**Repair research complete with limitations. Product and release readiness complete with limitations.**

Phase 12 adds opt-in, bounded state evidence and three one-site repair categories. It keeps the earlier Mini-C compiler, deterministic VM, Full C Clang analysis, ML profiles and private worker. Compiler validity, supplied expectations, worker outcomes, independent holdout and manual approval have distinct roles. [Architecture](phase12_architecture.md)

| Cohort | Holdout behavioral | Holdout exact |
| --- | --- | --- |
| Fresh documented defects | 0/2 | 0/2 |
| Authored injected faults | 3/3 | 3/3 |
| Archived diagnostics | 3/5 | 2/5 |

The same fresh documented cohort yielded 0/2 behavioral and exact under all three historical profiles. Phase 12 produced zero confirmed alerts and zero speculative suggestions on five correct controls. Both of the two guided recommendations passed holdout. The three injected recoveries account for all fresh recovery. The archived retained-run offset counterexample changed from 10 to the expected 0 via the replacement candidate. The fixed comparison set of 82 transformations preserved signatures.

[Baseline and CI](phase12_baseline.md) · [Evaluation and ablations](phase12_generalization_evaluation.md) · [Counterexamples](phase12_holdout_validation.md) · [Provenance](phase12_dataset_provenance.md) · [Leakage](phase12_leakage_audit.md)

## Release readiness

- [x] Reviewable feature branch based on verified merged Phase 11.5.
- [x] Authored demo sources, full source diff, explicit approval and source-snapshot invalidation.
- [x] Local development and built production preview, including Monaco and compiler API.
- [x] Restricted worker and analysis-only path exercised.
- [x] Versioned evidence and replay commands.
- [ ] Hosted Codespaces HTTP/2 incident reproduced and checked.
- [ ] External human adaptation review and expanded documented-defect coverage.

No deployment or public release was created. Live Ollama status is `NOT_VERIFIED`. [Codespaces validation](phase12_codespaces_validation.md) · [Demo](phase12_demo_guide.md) · [Security](phase12_security.md) · [Phase 13 readiness](PHASE_13_READINESS.md)
