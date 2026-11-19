# Historical failure taxonomy

The taxonomy joins recorded case IDs to their original phase, observed outcome and repair category. It preserves reported ranks and candidate-hit flags. Missing candidates, candidates below first place, unsupported inputs and ambiguous behavior are distinct observations. Category-to-reasoning mappings identify areas for investigation. The historical results cannot establish a causal root cause for an individual miss.

Phase 4.5 rows retain the original live family ID and distinguish runtime failure, multiple passing alternatives, unsupported execution and abstention. Ambiguous cases carry no inferred ground truth.

```sh
python -m benchmarks.phase5_taxonomy --check
```

[Machine-readable taxonomy](../benchmarks/reports/phase5-failure-taxonomy-v1.json)
