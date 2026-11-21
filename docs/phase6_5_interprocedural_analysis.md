# Interprocedural analysis

Call evidence includes the callee, source span, parameter position, lexical reads, and simple caller values with integer offsets. Calls in a return slice are marked as possible value contributors. Phase 6's direct and mutual recursion classifications remain visible.

The engine propagates possible global reads and writes transitively. Straight-line literal and unmodified parameter returns can refine the return argument mask, including wrappers that forward parameters in a different order. General functions conservatively retain all parameter positions. Masks describe possible returned-value dependence. Evaluation order, side effects and termination can still depend on other values.

The extraction budget is 72 call sites across the program. Effects use up to five propagation passes. Truncated or unresolved call paths fall back to all globals and all parameters, with explicit incomplete evidence.
