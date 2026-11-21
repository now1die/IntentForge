# Phase 6.5 baseline

The default branch `phase-1-intention-benchmarking` was at `18ee487bae1ed2162771a95adcb1c22078a6f0ea`, the verified merge commit of [PR #11](https://github.com/now1die/IntentForge/pull/11). Phase 6.5 branched from that commit.

| Post-merge workflow | Conclusion |
| --- | --- |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44888239797) | Passed |
| [Python tests](https://github.com/now1die/IntentForge/actions/runs/44888239881) | Python passed, optional Ollama skipped |
| [Frontend tests](https://github.com/now1die/IntentForge/actions/runs/44888239790) | Passed |
| [Isolated Mini-C execution](https://github.com/now1die/IntentForge/actions/runs/44888239809) | Passed |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44888239811) | Passed |

The baseline passed 699 Python tests with two live-worker skips, 29 Chromium tests with six live-worker skips, and the frontend build. The compiler suite passed 220/220. The keyboard and array verification saw zero unexpected outcomes across 65 cases. The stress harness ran 3,758 cases.

Phase 6's original independent cohort remains archived separately. Its code-only exact recall was 5/16, with seven fault alerts and one correct-control alert. Phase 6.5 uses a different corpus.
