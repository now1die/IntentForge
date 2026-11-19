# Phase 4.5 evaluation

The final VM corpus is independent from Phase 4's replay, and its references come from mathematical formulas or explicit fixture expectations. There are 14 executable, fault, bounded or unsupported families, with 28 supplied vectors and 216 generated reference vectors. An additional unit test uses 240 reproducible arithmetic comparisons. The existing Phase 4 benchmark remains an independent historical regression. This phase did not train an ML model, tune a threshold or alter historical labels.

| Local measurement | Mean | Median | p95 |
| --- | ---: | ---: | ---: |
| Preparation | 1.448 ms | 1.467 ms | 2.198 ms |
| One observed vector | 0.081 ms | 0.041 ms | 0.231 ms |
| Verification | 1.721 ms | 1.498 ms | 4.240 ms |
| Verification with trace | 4.553 ms | 1.522 ms | 42.158 ms |
| Failure handling | 1.120 ms | 1.040 ms | 1.495 ms |
| Local gateway repair comparison | 284.576 ms | 266.652 ms | 382.352 ms |

The measured VM trace p95 was sensitive to individual samples. Five cold probe children took 254–267 ms wall and 253–265 ms CPU. Maximum observed child RSS reached 38,592 KiB. These package-startup measurements and the six comparison cases describe a local run and provide a small sample for performance comparison. The report also records logical cells, depth, step counts and trace truncation per fixture.

The isolated repair corpus has six families and three labeled references. Candidate recall, static top-1 and static top-3 were 3/3 on the labeled subset. Four of five executable candidates passed supplied tests, and one failed at runtime. One case had multiple matches with seven differing probe observations. Two cases yielded no executable repair candidates. Every result required approval. Eight simultaneous requests returned two bounded executions and six capacity responses. The service recovered for a follow-up capability request.

Run the VM report without Docker. Run repair evaluation and cost measurement against the verified container.

```sh
python -m benchmarks.phase45_vm --check
python -m benchmarks.phase45_isolation
docker exec -i "$container" python - < deployment/minic_metrics.py
```

Raw results are available for the [VM](../benchmarks/reports/phase45-vm-v1.json), [repair and concurrency](../benchmarks/reports/phase45-isolation-v1.json) and [worker costs](../benchmarks/reports/phase45-worker-cost-v1.json). The [final review](PHASE_4_5_FINAL_REVIEW.md) records historical checks.
