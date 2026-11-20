# Phase 5 final review

**Complete with limitations.** In the frozen internal cohort, the new generators found more adjudicated repairs, and supplied behavioral expectations promoted one additional reference to first place. The structural scan also produced more false alerts on the five correct controls. Public execution remains disabled.

| Workstream | Delivered | Reproduce |
| --- | --- | --- |
| A · Code-only discovery | Located, binding-aware evidence with separate alert, false-positive and abstention metrics. Historical decisions are categorized by case ID. | [Static analysis](phase5_code_only_analysis.md) · [Taxonomy](phase5_failure_taxonomy.md) |
| B · Candidate generation | Four evidence-based additions, including two-site argument and accumulator repairs. Existing edit validation and the review requirement remain in place. | [Generation](phase5_candidate_generation.md) |
| C · Review ranking | Comparable v4 and structural-feature experiments use one candidate pool. Deterministic static rank is deployed. Isolated evidence has its own order and retains multiple matches. | [Ranking](phase5_behavior_guided_ranking.md) |
| D · Disagreement | Typed boundary and combination probes prioritize newly separated pairs within the shared work ceiling. Users supply any expected outputs. | [Probes](phase5_disagreement_probes.md) |
| E · Evaluation | Frozen, audited partitions with internally authored programs and fixture-backed specifications. Separate static, natural-language, explicit and live results. | [Provenance](phase5_dataset_provenance.md) · [Results](phase5_generalization_evaluation.md) |
| F · Workbench and safety | Phase 5 opt-ins, evidence provenance, explicit approval, source invalidation, dedicated tests and CI on the same isolation profile as Phase 4.5. | [Workbench and genuine captures](phase5_workbench.md) · [Security](phase5_security.md) |

## Local regression

The full isolated Python run passed 669 tests, including 18 dedicated Phase 5 checks. The TypeScript/Vite build passed. The isolated Chromium suite covered the new structural and live workflows, including user approval and entering an expected value after selecting a probe. Historical corpus and training checks from Phase 1 through 4.5 reproduced, along with the 12-case Clang analysis benchmark and the original Phase 4.5 isolated repair benchmark. The compiler passed 220 cases. The keyboard and array regression had zero unexpected results across 65 cases. The stress suite ran all 3,758 inputs.

CI replays the static reports and runs the isolated benchmark and the real workbench in Chromium. GitHub Actions results are attached to the PR head. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`. The optional fallback paths remain covered by regression tests.

The code-only results support continued local research. The set is small, internally authored, includes one disclosed near structural match and cannot establish generalization to external production code. Phase 5.5 needs independently authored families and more correct controls before broadening the generator or selecting learned ranking. Public execution requires separate assessment.

[Architecture](phase5_architecture.md) · [Phase 5.5 readiness](PHASE_5_5_READINESS.md) · [Baseline](phase5_baseline.md)
