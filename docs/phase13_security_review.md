# Execution boundary review

The browser and the ordinary API perform source analysis. Interactive verification uses the loopback gateway and an owner-private Unix socket to reach a separate non-root Linux VM worker. The tested container used no network, a read-only root, dropped capabilities, no-new-privileges, seccomp and bounded CPU, memory, processes and temporary space. The gateway checks returned candidate and source identities. Worker protocol 8 carries the inherited bounded operations. Full C remains Clang analysis only.

The private launch procedure and isolation tests cover the enabled and disabled gateway states. Browser tests exercise review invalidation on source, vectors and limits. Approval applies a reviewed change as one source update. The benchmark's offline replay of reviewed, pinned Python and JavaScript specimens is a developer tool outside the request path. [Isolation procedure](phase4_5_execution_isolation.md) · [Controls and assumptions](phase4_5_security.md)

The analysis-only hosting option serves the built frontend with the existing API bridge and disabled public execution. Private interactive verification additionally needs a compatible Linux container host, a private socket, and loopback access. A static file host alone can display the editor but needs the backend for compiler analysis.
