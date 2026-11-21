# Adaptation fidelity

The replay runs pinned Python function bodies and compiles the archived Java sources with their interface. It compares the original and fixed outcomes against the corresponding Mini-C variants for every discovery and holdout input. All four pairs agreed across 29 inputs, or 58 revision-specific comparisons. Each fix also agreed with the separately computed expected result.

Python floor division on the recursive midpoint is carried over explicitly. Python absence becomes `-1`, and recursion exhaustion is mapped to `CALL_DEPTH`. Mini-C and Java index failures share `ARRAY_BOUNDS`. The LCM adaptation uses equivalent nonnegative iterative GCD. Java lower-bound adapts Comparable values as signed integers, and the rotation case restricts long inputs to immediate original pivots to preserve deterministic replay. [Pin and domain manifest](../benchmarks/phase10_data/manifest-v1.json) · [Outcome replay](../benchmarks/reports/phase10-upstream-v1.json)
