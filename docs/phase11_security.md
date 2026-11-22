# Execution boundaries

The ordinary API performs bounded analysis over checked compiler terms. Runtime checks use the direct loopback gateway and owner-only directory containing the private Unix socket. The disposable worker is non-root with seccomp, a read-only filesystem, no networking and dropped capabilities. CPU, memory, wall time, process, concurrency, vector and candidate limits apply. The worker shares a 200,000-step VM budget across the batch.

Phase 11 uses private batch profile `8` with existing identity checks. The original result remains classified as a mismatch, an agreement, a runtime failure or an execution limit based on independently observed evidence. Public execution is disabled. Full C uses Clang analysis. Candidate review and source-snapshot checks precede atomic approval. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.
