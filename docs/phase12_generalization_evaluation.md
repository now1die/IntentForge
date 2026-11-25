# Generalization evaluation

Run `python -m benchmarks.phase12_evaluate --check` and repeat with `--live --check` when the private worker is available. The first report checks historical profiles 10.5, 11 and 11.5, the state-only profile, all three components independently and the full profile. The live report tests the historical and full profiles via the worker. The offline VM runs solely as a regression tool.

Phase 12 isolated results were 0/2 exact and behavioral for new documented faults and 3/3 exact and behavioral for authored faults. The Wilson 95% intervals are [0, 0.658] and [0.438, 1] respectively. Each individual component repaired one of the three authored faults by itself. Code-only Phase 12 recovered 0/5 exact and 0/5 behavioral on the independent faults. These experiments provide no measured fresh documented recovery gain. [Static ablations](../benchmarks/reports/phase12-static-v1.json) and [isolated results](../benchmarks/reports/phase12-live-v1.json)
