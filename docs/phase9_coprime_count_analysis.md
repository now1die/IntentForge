# Archived coprime-count analysis

The archived program calls a helper from its counting predicate. The helper
computes Euclidean remainder updates until an evolving divisor becomes zero.
Its exit depends on loop-carried values and a data-dependent number of steps.
The Phase 9 affine summary requires an invariant induction step and a
supported pure predicate, so the archived program remains unsupported.

Phase 9 handles input-dependent but invariant steps and small transfers over
multiple scalar locals. Neither extension supplies a sound reusable summary
for a nested Euclidean dependency. The historical diagnostic is excluded
from the independent final cohort.
