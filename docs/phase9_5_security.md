# Security and compatibility

The existing owner-only Unix socket, loopback admission, non-root Linux worker,
seccomp, read-only filesystem, and process, memory and CPU limits remain in
force. Engine 95 maps to private profile 8 and uses the existing 200,000-step
shared VM budget and identity checks. Public execution remains disabled.
Full C remains Clang analysis-only.

Static analysis projects finite scalar and fixed-cell facts. The independent
provenance harness runs selected pinned examples as a separate tool through
Node and Java. The normal analysis process has no external execution path.
The profile tests reject forged runtime evidence and Full C execution requests.
Live Ollama was unavailable. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.
