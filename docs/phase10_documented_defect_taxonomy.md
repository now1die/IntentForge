# Documented defect taxonomy

| Cohort | Symptom | Source mechanism |
| --- | --- | --- |
| Independent Python recursive binary search | Recursion exhaustion on absent keys | Missing empty-interval base case |
| Independent Python LCM | Division by zero for two zeros | Missing zero-product guard |
| Independent Java lower bound | Returns a later equal element | Equality exits before left refinement |
| Independent Java rotation pivot | Negative neighbor access on short arrays | Boundary assumptions and pivot loop update logic |
| Archived recursive search | Array bounds failure | Inclusive caller endpoint off by one |
| Archived expanding search | Wrong hit or wrong absence code | Growth-to-search handoff and absence encoding |
| Archived missing member | Wrong result | Missing minimum/maximum scan and unsupported XOR helper |
| Archived coprime count | Wrong count | Caller predicate around a data-dependent pure helper |

The four independent defects are translated numeric snippets from documented fixes. The injected faults and archived diagnostic cases have separate result denominators. [Pinned provenance](../benchmarks/phase10_data/manifest-v1.json)
