# Mini-C runtime semantics

- Integers are checked signed 32-bit values. Intermediate arithmetic and
  updates are checked. Unary minus admits the literal spelling
  `-2147483648`. Division truncates toward zero, and remainder is
  `a - quotient*b`. Zero divisors and an out-of-range quotient are errors.
- Booleans are a distinct type. Conditions, negation and logical operands
  require booleans. Logical AND and OR short-circuit. Arithmetic and
  relational operators require integers, and equality compares like types.
- Binary operands and function arguments evaluate from left to right.
  Assignment resolves its target first, including evaluation of an
  array index exactly once. Compound assignment reads the old target
  before evaluating its right operand. Assignment returns the stored
  value. Prefix updates return the new value, and postfix returns the old.
- Parameters are scalars passed by value. The outer function block
  shares their lexical scope. Functions look up globals through that
  frame, independently of the caller's locals. Inner blocks and for
  loops get their own scopes.
- Local scalar and array cells begin uninitialized. Reading an
  uninitialized cell fails. Global scalar storage is zeroed before
  explicit initializers run in declaration order. Global arrays are
  zero-filled when their declaration runs. Accessing a global array
  before allocation fails. Array lengths must be positive integers.
- A for-loop continue executes the update before the next condition.
  A break exits the innermost loop. Return propagates through nested
  blocks and loops. Void helpers can return without a value or fall
  through. Reaching the end of a value-returning function raises an error.
- Every vector starts with fresh globals, frames and storage. Supported
  operations do not observe the clock, system randomness or external I/O.

Read the [language inventory](phase4_supported_language.md) for admission
restrictions and the [execution limits](phase4_execution_limits.md) for
failure and accounting behavior.
