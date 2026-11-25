# Phase 12 architecture

Opt in with engine profile `12` in either workbench panel. The Python intention pipeline composes it with Phase 11.5 and earlier profiles. Requests use the same API endpoints, sources and snapshot hashes. The execution gateway still uses worker protocol 8.

The compiler supplies AST nodes, signed types, lexical bindings and source spans. The existing CFG and reaching definitions feed the independent state pass. State facts restrict selected inherited proposals and produce bounded candidate edits. The existing finite projection checks the supplied expectations and the normal compiler candidate validator checks the changed source. The private worker can separately execute discovery comparisons and independent evaluation uses verification-only requests for holdout.

See [semantic state](phase12_semantic_state.md), [candidate generation](phase12_candidate_generation.md) and [security](phase12_security.md).
