# Execution and security

Public engine 9 uses the existing local-only gateway and private profile 8.
The ordinary API performs bounded static projection. Worker-generated
observations come through the private owner-only socket. Existing request
limits, verified source identities and the 200,000-step shared VM budget
continue to apply.

The worker uses a disposable non-root Linux process, seccomp, read-only
filesystem, no network, process and concurrency bounds, and CPU, memory and
wall-clock limits. The existing isolation regressions exercise public
admission and verified return identities. The Phase 9 test also checks that
client-provided runtime evidence is rejected and that Full C stays
analysis-only. Live Ollama was unavailable.
`LIVE_OLLAMA_STATUS=NOT_VERIFIED`.
