# Security and compatibility

Public execution remains disabled by default and the gateway requires direct loopback access to an owner-only Unix socket. Mini-C runs in the existing restricted worker. The disposable non-root process, seccomp policy, network and filesystem restrictions, CPU and memory bounds, deadlines, concurrency limits, candidate/vector caps and shared 200,000-step budget are preserved. Clang remains analysis-only.

Worker evidence must match program, candidate, entry and test identities before the gateway classifies a fault. Probe observations never populate trusted expectations. The Phase 7 additions are opt-in and legacy response shapes are tested. Approval requires a current workbench snapshot and an explicit user action.

`LIVE_OLLAMA_STATUS=NOT_VERIFIED` when there is no live local Ollama service. The tool remains optional.
