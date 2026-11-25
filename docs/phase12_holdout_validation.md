# Holdout validation

The evaluator generates candidates from discovery vectors alone. Independent holdout is sent to the worker as verification-only requests against each discovery-compatible source. Reports record original and candidate outcomes, candidate IDs, exact references, observed steps, and recommendation status. Sampled agreement does not establish whole-program correctness.

The archived inherited candidate `IR-0a1b441390db` passed discovery and returned 10 on `[0,10,9,3,5]`, where expected output was 0. The original raised `ARRAY_BOUNDS`. The new candidate returns 0. The frozen inputs were preserved. [Archived candidate record](../benchmarks/reports/phase12-static-v1.json)
