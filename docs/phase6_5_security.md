# Security and deployment

Profile 65 adds static analysis in the API process and reuses the existing local restricted worker for observations. The private batch schema still accepts versions 4 and 5. The gateway continues to check source, entry, candidate, test-vector and probe identity. Request models reject fabricated observed outcomes. The workbench invalidates its snapshot when inputs or execution settings change.

Public execution stays disabled by default. The supported live profile uses a private Unix socket, non-root disposable worker processes, seccomp, capped CPU, address space and process count, read-only filesystem, no networking, deadline and concurrency checks. Tests and probes share one 200,000-step budget per batch. Full C remains analysis-only in the existing Clang pipeline.

`LIVE_OLLAMA_STATUS=NOT_VERIFIED`. No local Ollama service responded. The compiler, static engine and workbench do not depend on it.
