# Affine counting summaries

The loop model accepts one top-level `for`, a scalar accumulator seed and a
scalar return. The compiler identifies the loop header and latch. Its induction
variable moves by a positive or negative constant toward a pure invariant
bound. The summary computes the size of the arithmetic progression, checks
the final latch for int32 overflow, and counts points satisfying the optional
pure predicate. It applies a constant accumulator increment or decrement.
Because each accumulator update has the same signed increment, the seed and
final value bound the intermediate values.

Projection is capped at 64 points per supplied vector. At most one source site
changes in loop synthesis. Eligible sites include initialization, comparison
strictness, the predicate and literal step and increment magnitudes. Each
witness identifies the original guard, latch, accumulator, predicate and return
locations.

The archived coprime-count program calls a Euclidean helper with a data-dependent
loop in its counting predicate. The pure scalar predicate abstraction cannot
establish that relation. The engine abstains. The cohort also preserves
variable-increment and mixed-update loops as unsupported cases and controls.
Reversing comparison operands or inserting unrelated shadow scopes can make a
supported loop fall outside the current canonical shape.
