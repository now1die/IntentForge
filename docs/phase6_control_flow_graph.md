# Mini-C control-flow graph

The graph has located entry, exit, branch, statement, return, loop-header, loop-latch and transfer blocks. Edges distinguish true and false conditions, loop back edges, break, continue and return. A for-loop initializes before reaching its header. Continue reaches the update latch, and break reaches the continuation after its innermost loop. A return connects directly to exit.

The graph omits a branch edge only when the Boolean predicate is a literal, and treats an omitted for condition as true. Reachability is graph reachability over these conservative edges. Runtime faults and contradictory nonliteral predicates can make modeled paths infeasible. Source IDs are deterministic for a specific source snapshot. Compiler-invalid input returns incomplete evidence. The Phase 6 endpoint gives a located-shape instruction when the legacy parser encounters an unsupported bare declaration under a control statement.

```sh
python -m pytest -q tests/test_phase6.py -k 'cfg or reaching'
```
