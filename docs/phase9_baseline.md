# Phase 9 baseline

[Phase 8.5 PR #16](https://github.com/now1die/IntentForge/pull/16) merged into
`phase-1-intention-benchmarking` at `4affbc3d08a72b477f77d8008372e1ffedc506ba`.
The fetched default tip matched that commit. Phase 9 branches from it as
`phase-9-semantic-robustness-validation`.

| Post-merge workflow | Conclusion |
| --- | --- |
| [Python tests](https://github.com/now1die/IntentForge/actions/runs/44931393584) | Passed, optional live Ollama skipped |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44931393614) | Passed |
| [Frontend tests](https://github.com/now1die/IntentForge/actions/runs/44931393625) | Passed |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44931393578) | Passed |
| [Isolated Mini-C execution](https://github.com/now1die/IntentForge/actions/runs/44931393696) | Passed |

Local baseline checks reported 781 Python tests passed with eight skips and
36 Chromium scenarios passed with 12 skips under the default hosted
configuration. The frontend build succeeded. The archived Phase 8.5
evaluation measured 10/14 exact holdout repairs, 11/14 faults with a
behaviorally acceptable candidate, 13/14 supplied-test mismatch detections,
and 0/14 confirmed alerts on correct controls. Four archived metamorphic
comparisons changed the candidate categories. Phase 9 replays those four as
diagnostics and scores a different final cohort.
[Phase 8.5 review](PHASE_8_5_FINAL_REVIEW.md)
