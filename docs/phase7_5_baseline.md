# Phase 7.5 baseline

The fetched default branch `phase-1-intention-benchmarking` pointed at `47e5621b7945f72dd1a1bb7c12df3c48494fe8b6`, the verified merge of [PR #13](https://github.com/now1die/IntentForge/pull/13). The feature branch starts at that commit.

| Post-merge workflow | Conclusion |
| --- | --- |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44894991233) | Passed |
| [Python](https://github.com/now1die/IntentForge/actions/runs/44894991228) | Passed. Optional Ollama skipped |
| [Frontend](https://github.com/now1die/IntentForge/actions/runs/44894991266) | Passed |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44894991192) | Passed |
| [Isolated Mini-C](https://github.com/now1die/IntentForge/actions/runs/44894991302) | Passed |

The local baseline passed 739 Python tests with five restricted-worker skips, 31 Chromium scenarios with eight restricted-worker skips, and the frontend build. Historical static replays, compiler, keyboard and array verification, and the stress harness reproduced. The older Phase 7 cohort reported 6/19 exact guided repair recovery, 0/6 on external adaptations and two shadow-scope inconsistencies. Those archived cases are used for diagnosis and regression.
