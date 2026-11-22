# Adaptation fidelity

Pinned Python, JavaScript and Java sources execute in separate temporary-directory harnesses. Both revisions agreed with their Mini-C adaptations on 24 family inputs, yielding 48 revision-specific comparisons. Corrected versions also agreed with the independent expected outputs.

Python recursion exhaustion maps to `CALL_DEPTH`. The selected Java path is the single-row entry, so its observed column is preserved and a Java bounds exception maps to `ARRAY_BOUNDS`. The numeric JavaScript mean adaptation accepts only integral means. It represents the old nonnumeric empty outcome as a checked division fault and the fixed empty rejection as a distinct numeric sentinel. [Pin manifest](../benchmarks/phase11_data/manifest-v1.json) · [Direct replay](../benchmarks/reports/phase11-upstream-v1.json)
