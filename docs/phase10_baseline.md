# Phase 10 baseline

Phase 10 starts at `b86b6d0959a94afdeef9f9402e0f5d3b9438d2d4`, the merge commit of PR #18 on `phase-1-intention-benchmarking`. The local baseline passed 806 Python tests with 11 skips and 40 Chromium tests with 14 skips in hosted mode. The frontend production build succeeded.

All five post-merge workflows completed successfully. Python included the optional Ollama skip.

| Workflow | Verified run |
| --- | --- |
| Clang full-C analysis | [44939938360](https://github.com/now1die/IntentForge/actions/runs/44939938360) |
| Python tests | [44939938344](https://github.com/now1die/IntentForge/actions/runs/44939938344) |
| Frontend | [44939938353](https://github.com/now1die/IntentForge/actions/runs/44939938353) |
| Benchmark validation | [44939938392](https://github.com/now1die/IntentForge/actions/runs/44939938392) |
| Isolated Mini-C execution | [44939938374](https://github.com/now1die/IntentForge/actions/runs/44939938374) |

The previous engine did not recover any of the four archived Phase 10 diagnostic references. [Archived diagnosis and Phase 10 comparison](../benchmarks/reports/phase10-static-v1.json)
