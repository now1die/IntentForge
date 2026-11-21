# Loop layout normalization

The CFG supplies one reachable `for` header with one latch, a true body edge
and a false exit. The analyzer follows linear prefix and exit regions through
integer declarations, including nested lexical scopes. It preserves evaluation
of initializers, even when their values are unused.

An ordered comparison with the induction binding on the right is normalized
to the equivalent relation for iteration accounting. An edit to strictness
still targets the operator in the original source. The model accepts equivalent
latches including increment, subtraction assignment and a direct assignment
with the induction binding on either side of pure addition. Integer bound
expressions and latch operands that depend on mutable loop state are outside
the abstraction. This preserves the binding and evaluation constraints that
justify normalization.
