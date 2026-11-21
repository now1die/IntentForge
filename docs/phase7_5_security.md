# Security and compatibility

Engine 75 remains opt-in. Its local gateway reuses private worker protocol 7, an owner-only Unix socket and direct loopback access. The disposable non-root execution process retains seccomp restrictions, read-only files, disabled network access, CPU, memory and process bounds, deadlines, concurrency controls, candidate/vector caps and the shared step budget.

The API does static synthesis and validates the programs and execution identities returned by the worker. Conflicting expectations for identical inputs are rejected. Inputs from probes keep their observations separate from expectations. Manual application requires a current snapshot and an explicit action. Public execution remains disabled and full C remains Clang analysis-only.

`LIVE_OLLAMA_STATUS=NOT_VERIFIED`. No local service was available during verification.
