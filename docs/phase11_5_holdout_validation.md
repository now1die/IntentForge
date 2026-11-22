# Holdout validation

The harness sends only discovery inputs to candidate generation. Every discovery-passing candidate is submitted to a fresh restricted-worker request using its own source snapshot and separate held-out vectors with `compare_candidates=false`. It verifies the candidate's returned identity and requires an empty candidate list on that response.

Six of seven candidates passed this check. The inherited retained-run proposal read the first physical cell on empty logical input. The counterexample `[0, 10, 9, 3, 5]` had expected value 0 and candidate result 10. It was never recommended. Both known external adaptations and the archived interpolation experiments have separately labeled scopes in their reports. [Per-candidate results](../benchmarks/reports/phase115-live-v1.json)
