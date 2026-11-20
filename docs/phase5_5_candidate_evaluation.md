# Candidate generation evaluation

The admitted code-only final cohort yielded seven validation attempts and seven compiler-valid candidates. The returned identities were distinct. One candidate combined two edit sites. Exact reference recall, edit-location recall, static top-1 and static top-3 each measured 2/19. The exact matches repaired the final palette bound and the nested loop progress binding. The external-adaptation group recovered 0/11 references.

The end-to-end analysis median was 3.14 ms in the recorded local run. Unrecovered categories include recurrence, incorrect base cases, return dependencies and initialization. Withholding an accumulator hypothesis removed a known wrong-sign reference. The report separates these generation misses from ordering on the available pool.

The Phase 5 baseline for this cohort recovered 3/19 candidates. Evidence-gated ordering, v4 gating and pairwise ranking reused the same seven eligible candidates. They all ended at 2/19 top-1 and top-3. The pairwise artifact scored two final candidates, while the selection cohort contained no eligible candidate to support promotion. Coverage under the review recommendation policy was 0/40. These data support abstention labels and deterministic ordering. No calibration curve was fitted.

```sh
python -m benchmarks.phase55_evaluate --check
```

[Candidate and ranking evidence](../benchmarks/reports/phase55-static-v1.json)
