# Phase 8.5 baseline

Phase 8 [PR #15](https://github.com/now1die/IntentForge/pull/15) was merged into
`phase-1-intention-benchmarking`. Its merge commit,
`6562139ac0889636b6faf3549f999e19ff65efdf`, was the fetched tip and the starting
point for `phase-8.5-branch-aware-repair`.

| Post-merge workflow | Conclusion |
| --- | --- |
| [Python tests](https://github.com/now1die/IntentForge/actions/runs/44925099750) | Success, with the optional live Ollama check skipped |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44925099780) | Success |
| [Frontend tests](https://github.com/now1die/IntentForge/actions/runs/44925099798) | Success |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44925099775) | Success |
| [Isolated Mini-C execution](https://github.com/now1die/IntentForge/actions/runs/44925099748) | Success |

The baseline local Python suite reported 768 passed and seven skipped. The
Chromium run reported 33 passed and 11 skipped under the default execution
configuration. The frontend built successfully. The historical benchmark,
compiler, keyboard/array and stress commands completed. The compiler passed
220/220 fixed cases, the keyboard and array harness logged zero unexpected
outcomes over 65 cases and the stress harness processed 3,758 cases.

The archived Phase 8 cohort is unchanged. Phase 8 had 19/23 exact guided repairs
pass holdout, detected 22/23 supplied-test fault mismatches and confirmed 0/23
control alerts. Two discovery-passing proposals failed holdout. The historical
report gives the original denominators and uncertainty intervals.
[Phase 8 review](PHASE_8_FINAL_REVIEW.md)
