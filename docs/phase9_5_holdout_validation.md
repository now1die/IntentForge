# Independent holdout

Only discovery inputs are supplied to generation. Each discovery-passing
candidate gets a fresh worker request as an original program, with separate
vectors and candidate comparison disabled. The gateway checks source and
vector identities. Exact token-reference matches and other candidates that meet
both finite suites are counted separately.

The fixture manifest records the checked domains and every vector. Upstream
translation checks and archived recovery are reported separately from new
holdout results. Holdout counterexamples never enter synthesis.
[Frozen vectors](../benchmarks/phase95_data/cases-v1.json) ·
[Isolated report](../benchmarks/reports/phase95-live-v1.json)
