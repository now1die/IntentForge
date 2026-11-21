# Nonunit recursion

The progress witness identifies one modeled atomic base guard, its lexical parameter and threshold, and its directed self-call arguments. It follows direct recursive values and unique scalar declarations in a bounded CFG. An argument can have a constant affine offset, a signed symbolic offset, or an unresolved relationship. The witness notes returned-value dependence. Unsupported recursive layouts are marked incomplete.

Changing an existing fixed step requires at least two distinct typed supplied inputs reaching the recursive branch. The engine explores a small set of fixed steps between one and four. An unchanged integer parameter can also be a symbolic step when multiple distinct positive sample values make it a plausible alternative. Other arguments remain unchanged. An unchanged guarded argument can justify a one-unit hypothesis even when its return is wrapped in arithmetic.

The guard establishes direction within the modeled layout. It leaves domain coverage, stride intent, checked arithmetic and termination open. Multi-parameter relational guards, coupled updates and general affine expressions remain outside the synthesis rule.
