# Coprime count

The archived helper repeatedly replaces its operands with a divisor and
remainder. The guard and progress depend on the two evolving operands.
The affine latch check cannot establish a loop-invariant endpoint or supported
progress for that helper, so the archived coprime-count case still abstains.
A future abstraction would need a provably decreasing measure and checked
signed-remainder behavior.
