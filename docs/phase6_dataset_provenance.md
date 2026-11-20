# Phase 6 dataset provenance and evaluation policy

The Phase 6 final cases are frozen before final scoring. The corpus includes independently specified Mini-C programs, with developer-authored defects and correct controls. MIT-licensed adaptations are based on the pinned TheAlgorithms/Python revision in the manifest. Those labels, ports and test vectors were created for this project. No independent human adjudication took place. Internal fixtures have no separately published reuse license.

The separate oracle sources include mathematical formulas, standard-library arithmetic, independently calculated integer results, and partial observations. Expected values are frozen independently of engine proposals. The historical Phase 5.5 cohort remains a historical comparison. We audit Phase 6 against prior JSON source and reference cases and keep source families within partitions. Historical exact or alpha matches and long near matches are quarantined. Cross-split near matches remove a non-final family when possible. Shared edit shapes are reported separately.

Phase 6, Phase 5 and Phase 5.5 are evaluated on the admitted cohort. The opt-in deterministic ordering is selected by default. Same-pool alternatives would require a top-rank gain on selection cases without extra false recommendations. No new ranker or calibration model is fitted. Frozen final metrics are held separate from selection.

Reproduce the corpus with `python -m benchmarks.phase6_fixtures /path/to/pinned-upstream-files`. Download the manifest's exact paths at its pinned revision into that directory using each original basename. Compare the resulting case and upstream hashes to the committed manifest. Routine evaluation uses the committed data and runs offline.

[Manifest](../benchmarks/data/phase6/manifest-v1.json) · [Frozen cases](../benchmarks/data/phase6/cases-v1.json) · [MIT notice](../benchmarks/data/phase6/TheAlgorithms-MIT.md)
