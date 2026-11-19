# Phase 5 workbench

Select **Phase 5 structural evidence** on the Intention tab. In Code only mode, the structural scan shows located hypotheses, assumptions, insufficient evidence and scan limits. Choose a candidate to see individual edits and compiler validation before approval.

On a verified local deployment, enable **Compare repair candidates** and **Phase 5 repair and probes** under interactive behavioral verification. An empty list starts an observational comparison. Candidate rows retain static rank and show their behavioral review position. The test table presents supplied expectations and observations. Probes show the basis, cost and pairs separated. Selecting an input adds it to the test list for you to supply its expected result. Changes to source, entry point, tests, comparison mode or execution settings invalidate the result. Explicit approval applies a selected candidate.

```sh
INTENTFORGE_PHASE5_CAPTURES="$PWD/audit/phase5" npm --prefix frontend test -- phase5.spec.ts
```

[Two-site structural review](../audit/phase5/structural-review.png) · [Live observational probes](../audit/phase5/isolated-probes.png)
