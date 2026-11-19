# Phase 4 readiness

The typed oracle boundary, program identity, execution limits and
supplied-vector checks are ready for an isolated Mini-C interpreter
prototype. Start with trusted fixtures and deterministic evaluation of
the language subset. Add array bounds, call depth and cost accounting,
unsupported cases, trace limits and runtime diagnostics before
connecting any executor to user-supplied code.

Deploying any executor requires an explicit threat model, isolation tests,
failure semantics and an independently reviewed deployment boundary.
Static compiler evidence, candidate generation, oracle checking and
user approval are independent stages. C execution and intention
inference remain separate research tracks.
