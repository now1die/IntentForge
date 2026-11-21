# Phase 8 baseline

The fetched default branch `phase-1-intention-benchmarking` was at `dc1037c0e7300f76668283c65681ef0c234378d6`, the verified merge of [PR #14](https://github.com/now1die/IntentForge/pull/14). Phase 8 branches from that commit.

| Workflow on the merge commit | Result |
| --- | --- |
| [Clang](https://github.com/now1die/IntentForge/actions/runs/44897373075) | Passed |
| [Python](https://github.com/now1die/IntentForge/actions/runs/44897373146) | Passed, optional Ollama skipped |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44897373084) | Passed |
| [Frontend](https://github.com/now1die/IntentForge/actions/runs/44897373143) | Passed |
| [Isolated Mini-C](https://github.com/now1die/IntentForge/actions/runs/44897373140) | Passed |

The local baseline passed 753 Python tests with six restricted-worker skips, 32 Chromium scenarios with nine restricted-worker skips, and the frontend build. Historical static replays, compiler cases and stress benchmarks reproduced. The archived Phase 7.5 result of 16/24 guided exact repairs belongs to its own cohort. Phase 8's independent results use a new split and re-evaluate the older profiles on that split.
