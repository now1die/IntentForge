# Helper-mediated control flow

A projected helper takes typed scalar arguments by value and returns a scalar.
Supported bodies use local checked transfers, conditional returns and admitted
for loops. Acyclic expansion admits four functions with at most two call edges
in depth. Bindings and source spans remain local to each function.

The evidence distinguishes a false guard, break, continue and early return.
Continue uses the compiler's latch edge. Recursion, dynamic-size arrays,
global declarations and data-dependent while loops are unsupported by this
projection. The isolated worker retains its existing execution semantics.
