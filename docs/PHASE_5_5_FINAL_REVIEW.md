# Phase 5.5 final review

**Complete with limitations.** The revised opt-in gates withheld several misleading Phase 5 hypotheses. In the admitted final cohort, false alerts fell from 3/19 to 2/19, fault alerts fell from 5/19 to 3/19 and exact candidate recall fell from 3/19 to 2/19. None of the 11 external-adaptation faults yielded its exact reference in code-only analysis. Phase 5.5 keeps deterministic ordering and makes the evidence for abstention visible.

| Workstream | Outcome | Reproduce |
| --- | --- | --- |
| A · Corpus | 63 frozen cases, 52 admitted, 40 final. Verified upstream MIT provenance and independent reference checks. | [Provenance](phase5_5_dataset_provenance.md) · [Audit](phase5_5_leakage_audit.md) |
| B · Precision | All four gates evaluated on development controls. False alerts fell alongside recall. | [Heuristics](phase5_5_false_positive_analysis.md) · [Precision and recall](phase5_5_precision_recall.md) |
| C · Robustness | 146 behavior-preserving transformations. One exposed a guard-orientation dependence. | [Robustness](phase5_5_robustness.md) |
| D · Candidates and ranking | Generation measured separately. Same-pool rankers tied and selection provided no eligible gain. | [Candidates](phase5_5_candidate_evaluation.md) · [Selection policy](phase5_5_ranking_selection.md) |
| E · Behavior | 40 final original executions in the restricted profile. Test guidance maintained ambiguity and separated one qualifying pair. | [Behavioral evaluation](phase5_5_behavioral_evaluation.md) |
| F · Workbench and regression | Explicit opt-in, counter-evidence, snapshot invalidation, manual approval and retained worker limits. | [Workbench and captures](phase5_5_workbench.md) · [Security](phase5_5_security.md) |

## Verification

The local Python and Chromium suites include the new precision profile, the earlier Mini-C paths and the existing Clang analysis. Local historical checks replay the original corpus, audits, ML reports and VM benchmarks. The isolated workflow runs the Phase 4.5 repair benchmark together with the Phase 5 and 5.5 live replays. GitHub Actions results are attached to the PR. The optional local Ollama service was unavailable. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.

Phase 5 PR #9 was open at the requested base during implementation, so this delivery is stacked on the Phase 5 head. The Phase 5.5 PR stays open for review. If Phase 5 merges, retarget the Phase 5.5 PR to the default branch after verifying that the merge preserves its base changes.

[Baseline](phase5_5_baseline.md) · [Architecture](phase5_5_architecture.md) · [Phase 6 readiness](PHASE_6_READINESS.md)
