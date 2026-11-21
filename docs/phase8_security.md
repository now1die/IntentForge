# Security and deployment

Phase 8 stays opt-in. The API operates on compiler evidence and bounded arithmetic constraints. It has no new solver dependency and never dispatches Mini-C execution in process. The restricted worker retains its owner-only Unix socket, direct loopback gateway, disposable non-root processes, seccomp, no networking, read-only filesystem, CPU, memory, deadline, process, concurrency and shared 200,000-step limits. The public and prior private contracts are preserved, with domain admission added for private version 8.

Source, entry, candidate and test identities are checked before classifying runtime evidence. Probes with a declared domain are filtered in the worker. Answers from final tests are available only through the evaluation artifacts. The synthesis endpoint accepts independently supplied expectations and rejects fabricated observations. Applying a repair still requires the current source snapshot and an explicit action. Public execution remains disabled and full C stays Clang analysis-only.

`LIVE_OLLAMA_STATUS=NOT_VERIFIED`. The optional local service was unavailable during verification.
