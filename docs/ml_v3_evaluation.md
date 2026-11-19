# ML Generalization 3.0 evaluation

All code-only configurations ran on 26 held-out families with 18
adjudicable repairs. Candidate membership is asserted identical for
the v3 ordering comparisons. End-to-end legacy models use their own
candidate generation. Top-k counts match registered reference tokens.
A compiler-valid alternative can still differ from the selected
reference or change semantics.

| Code-only configuration | Top 1 | Top 3 | Candidate recall |
|---|---:|---:|---:|
| Original rules | 0/18 | 0/18 | 0/18 |
| Original ML | 0/18 | 0/18 | 0/18 |
| Original hybrid | 0/18 | 0/18 | 0/18 |
| Phase 2 contextual learned | 1/18 | 3/18 | 3/18 |
| Phase 2.5 deterministic | 2/18 | 4/18 | 4/18 |
| Phase 2.5 learned | 3/18 | 4/18 | 4/18 |
| v3 deterministic and full gated engine | 6/18 | 9/18 | 9/18 |
| v2 on the v3 candidate pool | 7/18 | 9/18 | 9/18 |
| v3 experimental pointwise or boosted | 7/18 | 9/18 | 9/18 |
| v3 experimental pairwise | 6/18 | 9/18 | 9/18 |
| v3 with new generation disabled | 2/18 | 4/18 | 4/18 |

Wilson 95% intervals are 16–56% for full v3 top 1 and 29–71% for
candidate recall. Phase 2.5 learned intervals are 6–39% and 9–45%.
These intervals are descriptive for this authored collection.
The new generator mainly recovers canonical bounds/indices, a second
return branch, paired independent array edits, and a typed argument
permutation. On the identical new pool the strongest learned models,
including v2, found one additional top-1 reference. v3 candidates are
compiler-valid in 18/24 cases, counting individual patches, with
remaining patches reducing diagnosed errors and labeled unverified.
Three of nine adjudicable inputs with a proposal missed the top
reference. Fifteen of 26 cases received no proposal. Mean and p95
end-to-end latency were about 2.7 ms and 6.0 ms for v3, and 2.9 ms
and 8.0 ms for Phase 2.5 learned in this run.

Six fixtures had matched requirement modes. Reference matches were 0/6
code-only, 6/6 natural language, and 6/6 with explicit expressions. The
cohort targets supported wording. Explicit repair is supplied-expression
matching. Natural language uses a constrained structured grammar, which
includes exclusive ranges, parenthesized negation, direct array access
and named accumulator arithmetic. Phase 2.5 formats for comparisons,
arithmetic, min/max, inclusive ranges and returned calls are also
supported. Ambiguous selectors and unsupported descriptions abstain.
There is no runtime verification.

The JSON report includes per-family results, per-category counts,
logic precision and recall, confirmed valid controls, candidate
validity, abstention, intervals and timing for all configurations.
[Machine-readable evaluation](../benchmarks/reports/ml-v3-evaluation-v1.json)
