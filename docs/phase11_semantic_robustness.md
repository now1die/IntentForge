# Structural robustness

Phase 10.5 missed the transformed iterative leftmost match because an otherwise direct return block contained an unused nested literal declaration. It missed the transformed recursive upper bound at base-case recognition for the same reason. The added scopes change compiler graph blocks and bindings. The returned binding and the surrounding interval remain equivalent.

Phase 11 follows the AST nodes and lexical boundaries through inert nested literal blocks. It preserves the original span of the return for a local refinement and leaves the irrelevant shadow scope in the source. It does not discard general statements or declarations in the return's own scope. Both archived cases kept their verified candidate effects after the repair. The evaluation records original and transformed sources, spans, bindings, CFG evidence, reaching-definition states and candidate results. [Shadow and broader metamorphic reports](../benchmarks/reports/phase11-static-v1.json)
