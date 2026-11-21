# Interprocedural repairs

Existing Phase 7.5 helper summaries admit small effect-free scalar helpers into the arithmetic projection. Phase 8 traces local aliases and scalar return dependencies across up to two helper levels. A helper edit is evaluated at every projected use while the actual source keeps its calls and execution order. Candidate return replacements must refer to an initialized local that is lexically visible at that return.

The helper-only ablation recovered two wrong returned intermediates. Combining it with arithmetic synthesis recovered additional offsets inside helpers. Uncertain global effects, assignments, arrays, branches in the arithmetic slice, and arbitrary call inlining remain unsupported. An edit in a shared helper may affect other callers outside the supplied entry-point evidence.
