# Phase 6 workbench

Select **Phase 6 program reasoning** under Intention. Open a function to inspect its modeled reachable blocks, conditions, calls, possible missing returns and source-located dependencies. Candidate review shows the assumption, supporting evidence, counter-evidence, compiler status and edit spans. Applying a review requires explicit approval.

In the restricted local profile, Phase 6 is available under interactive candidate comparison after enabling repair and probes. The view keeps static rank separate from behavioral order and shows runtime outcomes and trace. The original recursion example stops at the call-depth limit while the candidate returns the supplied expected result. Changing a test vector invalidates the review.

```sh
INTENTFORGE_PHASE6_CAPTURES="$PWD/audit/phase6" npm --prefix frontend test -- phase6.spec.ts
```

[Return dependency review](../audit/phase6/return-dependencies.png) · [Isolated recursive verification](../audit/phase6/isolated-recursion.png)
