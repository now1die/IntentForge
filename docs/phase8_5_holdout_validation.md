# Holdout validation

Development, selection, calibration and final families have separate roles and
family assignments. Within each scored final family, supplied inputs and
holdout inputs are disjoint. The case manifest pins labels, expected values and
upstream digests. The [frozen cohort](../benchmarks/phase85_data/cases-v1.json)
spells out every input and expected output.

The benchmark sends only the discovery rows to candidate generation. It sends
each discovery-passing candidate as an original source snapshot in a fresh
worker request with candidate comparison disabled and with only holdout rows.
The gateway verifies response identity and the evaluation records every
counterexample. Exact-reference matching uses the project's repair
normalization. Other candidates can earn finite behavioral agreement.

The relay grid contains nine specified pairs, four discovery points and five
holdout points. The boundary-gap fixture
`observed-disagreement-spacing-fault` passes its supplied tests and fails a
hidden test. Its supplied status remains unchanged and earns no confirmed
discovery fault. See the per-candidate evidence and counterexamples in the
[isolated report](../benchmarks/reports/phase85-live-v1.json).
