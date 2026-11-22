# Phase 11.5 baseline

The fetched default branch pointed to PR #21's merge commit `154a0087c626d8db7772a783086988470ba28098`. The feature branch was created from that integration. The local disabled-worker baseline passed 837 Python tests with 14 skips. All five post-merge workflows passed. The optional Ollama job was skipped.

| Workflow | Run |
| --- | --- |
| Clang | [45040328528](https://github.com/now1die/IntentForge/actions/runs/45040328528) |
| Python | [45040328526](https://github.com/now1die/IntentForge/actions/runs/45040328526) |
| Frontend | [45040328584](https://github.com/now1die/IntentForge/actions/runs/45040328584) |
| Benchmark validation | [45040328527](https://github.com/now1die/IntentForge/actions/runs/45040328527) |
| Isolated Mini-C | [45040328540](https://github.com/now1die/IntentForge/actions/runs/45040328540) |

The archived Phase 11 score was 2/3 behavioral and 1/3 exact on documented defects, and 4/4 behavioral and 3/4 exact on injected faults. Both archived shadow regressions produced candidates under Phase 11. The new cohort and archived diagnostics have separate denominators.
