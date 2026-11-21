# Multi-parameter recursion

`RECURSIVE_PARAMETER_PROGRESS` targets one unambiguous integer argument passed unchanged to a direct self-call despite a simple order guard against a literal. A one-unit change moves toward the modeled base branch. The candidate preserves the accumulator, index or other argument expressions in their existing positions. The analyzer requires both return sites to be modeled. Independent controls exercise increasing indices, unchanged accumulators, repeated arguments and asymmetrical updates.

Call mapping also exposes both endpoint offsets for interval recursion. Relational guards and mutual cycles remain analysis-only. The one-unit edit is a hypothesis about the step size and domain. Universal termination, overflow freedom and intended behavior require additional assumptions.
