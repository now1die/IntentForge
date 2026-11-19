# Phase 4 security boundary

The Mini-C oracle is available only to trusted in-process callers and
repository fixtures. The FastAPI application contains no execution or
repair-verification route. An HTTP request cannot submit runtime
evidence. Static analysis remains the default. The workbench ships
reviewed recorded examples and performs no execution or repair
application when displaying them.

The interpreter dispatches existing AST nodes. Its operations have
no access to filesystem paths, network clients, processes, host
registration, native execution, or dynamic Python evaluation.
Compiler admission, checked arithmetic, deterministic budgets,
bounded traces and explicit cleanup provide the verified internal
bounds. Dedicated tests cover resource ceilings and rejected evidence
injection.

Public isolation remains unverified. A future public service requires
an independently reviewed trust boundary, process-level termination
and CPU/memory limits, least privilege, no credentials or egress,
restricted mounts and deployment-level quotas. The existing Clang
worker analyzes full C separately. Its isolation does not authorize
executing C or Mini-C programs.
