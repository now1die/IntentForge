# ML Generalization 3.0 architecture

## Audit before implementation

The branch starts at merged Phase 2.5 commit `491675e`. Before editing,
`python -m benchmarks.phase25_evaluate --check` reproduced its decisions.
Phase 2.5 recovered 18 of 30 reference programs in its final candidate
pools. Ranking selected 15 deterministically and 16 with learning. Five
adapted tasks had no correct top-ranked code-only patch. Candidate
coverage, especially in valid logic cases without a diagnostic, is the
ceiling on ranking gains.

`intention_context` reconstructs lexical scope, AST relationships, types
and compiler diagnostics. It is not a control-flow or initialization
proof. `intention_candidates` covers diagnostic fit and local symbols.
`intention_recovery` recognizes adjacent computed returns, sibling
operator consensus, fixed literal indices, and selected two-argument
calls. This misses local values returned on a different branch,
multi-argument type permutations, and canonical loop bounds tied to
actual arrays. Candidate caps also compete with diagnostic combinations.
Two valid Phase 2.5 controls generated alerts. A computed unused value
can be intentional, and proximity alone does not establish intent.

The v2 learned layer mixes useful signal such as AST role, type fit,
binding history and diagnostic change with formal-name proximity and
initializer/write patterns strongly expressed by its mutation
scaffolds. A lexical prior write can belong to a branch not taken.
Two validation families per category and similar synthetic patterns made
large selection gains fragile. Historical results lost two top-1 matches
when learning replaced deterministic ordering on the same pool.
Compiler-diagnosed categories lack diverse unseen counterexamples, and
valid return, operator, call and multi-edit hypotheses lack adequate
independent ranking labels. The Phase 2 ranker is narrower still.

## Design

Use bounded, versioned generation, separating static contradictions and
typed evidence from peer analogy. A pure duplicate guard can support an
observation without specifying an edit. Every proposed patch is compiled,
deduplicated, associated with concrete evidence, and requires approval.

Rank only comparable candidates. Study shared pointwise, signed pairwise
and shallow gradient boosting on identical pools. Omit names and
mutation identities. Add lexical block, operand and static definition
context. Compare over held-out program families and retain deterministic
ordering for categories lacking evidence of a gain. Existing engine
versions and all historical model artifacts remain replayable.
