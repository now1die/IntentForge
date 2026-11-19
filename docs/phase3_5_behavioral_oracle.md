# Behavioral oracle contract

The Python `BehaviorOracle` protocol accepts text, an entry point,
typed test vectors, resource limits, and an optional candidate ID.
Version 1 results carry the SHA-256 of the exact source, the selected
function, optional candidate ID, observations, diagnostics, unsupported
constructs, and status. Status distinguishes matching supplied tests,
observed mismatch, unavailable, unsupported, limited, and unknown.
Compiler validity is tracked independently.

A trusted in-process caller may attach a result to an intention
analysis. Entry point, program fingerprint, candidate identity, compiler
validity and the supplied vectors must match. Matching results need
observations for every vector. Existing HTTP requests cannot submit
behavioral evidence. Tests attach fixture observations and reject stale
or injected evidence. This milestone performs no runtime verification.

Phase 4 can implement this protocol behind a separate trust boundary.
Required interpreter components are expression evaluation, call frames
and recursion limits, scoped variables and arrays, branches and loops,
deterministic step and memory accounting, return values, bounded traces,
runtime diagnostics and explicit unsupported constructs. Behavioral
evidence should remain separate from intent ranking and repair approval.
