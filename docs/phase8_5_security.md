# Phase 8.5 security and execution

Public profile 85 uses the existing local-only gateway and maps to private
worker profile 8. Requests use the existing source, vector and resource limits.
The gateway admits compiler-valid candidate snapshots and verifies returned
program identities before showing results. Public and Full C modes retain their
existing execution boundaries.

The isolated worker runs non-root without network access, with a read-only
filesystem, dropped capabilities, bounded CPU and memory, and a restricted
local Unix socket. The release test exercises these boundaries against the
Docker worker. The UI discards outdated evidence when the source, entry,
requirements, bounds, vectors, profile or execution settings change and
requires an explicit apply action on the current candidate.

Ollama is optional. The local endpoint had no listener during verification.
`LIVE_OLLAMA_STATUS=NOT_VERIFIED`.
