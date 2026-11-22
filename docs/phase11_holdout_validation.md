# Holdout validation

Only discovery vectors are sent to synthesis. Every candidate matching discovery is then submitted as a new original source with independent vectors and `compare_candidates=false`. The harness checks that the returned program identity matches the candidate and requires an empty alternative set for the holdout request.

All seven final candidates passed both suites. No candidate was contradicted in the frozen holdout, so this run produced no candidate counterexample. The two interpolation alternatives agreed on the final samples. Both recommendations passed. Archived interpolation and coprime repairs also passed their separate holdout. [Per-alternative discoveries and held-out results](../benchmarks/reports/phase11-live-v1.json)
