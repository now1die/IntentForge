# Loop boundaries and windows

The model admits an ordered invariant scalar bound, one integer induction
binding and an affine latch. It accepts reversed operands and ascending
nonnegative squared induction. The CFG preserves empty iterations, nested
indexed windows and distinct early exits.

The search toggles strictness or shifts a literal offset by one. Each sampled
loop row records its first and last visited index and iteration count. Repair
details retain the original source coordinates and show the replacement
alongside its sampled indices. Fixed local integer arrays are represented by
extent-checked facts. Reads require initialized cells, and candidate results
must agree with every supplied output.
