# Shadow-scope robustness

The archived `recursive-doubler` and `recursive-negator` cases lost their hypothesis when a nested block of unused literals was inserted in a helper. The old proof required a body containing exactly one return statement. The inserted locals had distinct lexical identities and did not reach the return. The new helper proof checks each reachable CFG expression and resolves local reads through their lexical declaration.

Both archived transformations preserved the original observed behavior and regained the recursive progress hypothesis. The new final cohort preserved hypotheses across all 286 VM-checked transformations, including renaming, reversed comparisons and branches, parentheses, shadow scopes, and independent declaration ordering. Additional controlled metamorphs exercise helper-local temporaries and reordered declarations, with snapshot, edit and behavioral validation.
