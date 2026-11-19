# Execution limits and failures

`ExecutionLimits` retains its defaults of 10,000 steps, 32 call frames,
and 4,096 live cells per vector. Its absolute caps are one million steps,
128 frames and 65,536 cells. A verification also shares a 200,000-step
budget across its vectors. Trusted repair comparison shares that
budget across all programs and executes at most four candidates.

- Statements, expressions, lvalue resolution, call entry, parameter
  binding, global reservation and each successful loop iteration each
  consume a step. Array allocation also consumes one step per element.
  Checks occur before the counted operation. Caller-side compilation is
  separately bound by source and AST admission limits.
- Each scalar binding, array binding and array element reserves one
  cell. Block and frame exit release local cells. The limit is logical
  Mini-C storage. It measures neither Python allocations nor RSS.
- Inputs are limited to 24,000 characters, 48,000 UTF-8 bytes, 3,000
  compiler tokens, and the existing nesting and expression limits. The
  oracle rejects trusted calls above 96,000 characters before hashing.
  At most 12 vectors and 16 arguments per vector are accepted.
- Tracing retains at most 64 events and 8,192 serialized bytes per
  verification. It records event kind, step, vector and native source
  span, with UTF-8 offsets and UTF-16 editor columns. It omits values,
  binding names and program text. Truncation is explicit.

Budget failures return `EXECUTION_LIMITED`. Invalid compiler input,
missing entry points, invalid vectors and unsupported features return
`EXECUTION_UNSUPPORTED` with distinct diagnostic codes. Division by
zero, bounds errors, overflow, invalid operations, uninitialized reads
and missing returns are reported under `BEHAVIOR_UNKNOWN`. Unexpected
interpreter failures report a generic internal-error code. Incomplete
runs can preserve earlier observations without claiming complete
test agreement.
