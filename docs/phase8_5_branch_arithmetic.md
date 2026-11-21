# Branch-aware arithmetic

The analysis walks compiler CFG edges, retaining a lexical environment for each
path. An initialized scalar declaration introduces a binding. An assignment
updates that binding on the path that reaches it. At a join, the return term
uses the environment that arrived through the selected branch. Each visited
initializer and assignment is checked even if its value does not reach the
return.

For each supplied input the projection records guard outcomes, the return
location and directly reaching definitions. For a candidate, the same
constraints are projected with its edits and report source spans in the original
snapshot. An edge with zero examples remains unobserved. A Boolean return can
also be projected as a predicate even when there is no explicit `if`.

There are at most eight modeled exit paths and 64 CFG visits. Calls, globals,
arrays, unsupported statement kinds and unsupported checked arithmetic cause
the new projection to abstain. A separate proof of reachability or equivalence
over all inputs is outside its scope.
