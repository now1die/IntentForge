# Phase 10.5 baseline

PR #19 was merged at `168f109385f9b2ec752e2a53c415dbda1a2b2167`. The fetched default branch, `phase-1-intention-benchmarking`, pointed to that integration commit. Phase 10.5 was branched from it. The local Python baseline passed 813 tests with 12 skips in the configuration without the worker.

All five Phase 10 post-merge workflows completed successfully. The optional Ollama job was skipped.

| Workflow | Run |
| --- | --- |
| Clang | [44944451400](https://github.com/now1die/IntentForge/actions/runs/44944451400) |
| Python | [44944451272](https://github.com/now1die/IntentForge/actions/runs/44944451272) |
| Frontend | [44944451364](https://github.com/now1die/IntentForge/actions/runs/44944451364) |
| Isolated Mini-C | [44944451262](https://github.com/now1die/IntentForge/actions/runs/44944451262) |
| Benchmark validation | [44944451456](https://github.com/now1die/IntentForge/actions/runs/44944451456) |

Phase 10 produced no candidate for the archived duplicate lower bound, short rotation pivot, zero-input LCM or shifted missing member. The four cases are diagnostic inputs for the new work.
