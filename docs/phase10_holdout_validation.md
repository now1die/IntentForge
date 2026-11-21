# Holdout validation

The gateway receives discovery inputs with typed outputs to generate and verify candidates. Every candidate that passes discovery is submitted as a new original with fresh held-out inputs and `compare_candidates=false`. The harness verifies the request and response source identities and expects an empty candidate set in the holdout response. The fixture enforces distinct vectors. The final holdout outcomes are recorded without feedback into discovery.

All six Phase 10 candidates passed discovery and fresh holdout, including both recommendations. There were no contradicted candidates in this pool. The archived recursive, expansion and coprime candidates separately passed their two held-out vectors each. The missing-member diagnostic produced no candidate. [Per-candidate held-out evidence](../benchmarks/reports/phase10-live-v1.json)
