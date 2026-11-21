# Phase 9 architecture

Engine 9 is an opt-in extension of Phase 8.5. The compiler still owns syntax,
types, scope and binding IDs. Its CFG and reaching definitions admit a small
class of single-loop transfer summaries, while Phase 8 arithmetic terms
model checked arithmetic and Phase 8.5 paths distinguish supplied examples
on different branches. The existing candidate contracts handle source edits,
compiler validation and manual review.

The public API adds `program_analysis.phase9` to the static result and
`specification.phase9` to the behavioral result when candidate comparison runs.
The separate `runtime_observation` field describes a verified original runtime
failure. Public engine 9 uses the established private worker profile 8.
