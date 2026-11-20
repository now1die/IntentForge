# Phase 5 dataset provenance

The frozen [corpus](../benchmarks/data/phase5-v1.json) contains 27 internally authored Mini-C programs with independently specified behavior, references where adjudicable, typed examples and adaptation notes. Reference outputs come from integer formulas or manually derived examples. The evaluator first checks that every labeled reference satisfies its separate test examples. The fixtures were authored in this project. This is neither an external benchmark nor a blinded author study.

The frozen manifest uses “Repository license” as a placeholder. IntentForge currently publishes no repository license, and the corpus carries no separate reuse license. The corpus contains no externally copied source or task text.

The admitted cohort has 25 distinct program families. Partitions contain 2 training-reserved, 2 selection, 2 calibration, 3 development and 16 final families. Training-reserved and calibration partitions are kept separate. The study fits no new model and calibrates no probabilities. The 16 final families include 10 adjudicable faults, 5 controls and 1 case with insufficient intent evidence.

The byte hash is pinned in the evaluator. The audit quarantined two non-final fixtures with exact alpha-normalized token matches to final cases before any ranking evaluation. No frozen final data was edited. It audits unique family IDs, exact cross-partition token structures, full vector reuse, duplicate specification text and exact matches against 750 historical source/reference representations. It reports shared repair categories and near matches. One development/final loop pair has 0.907 token similarity. The pairs have separate program specifications and references, and that overlap limits independence.

```sh
python -m benchmarks.phase5_evaluate --check
```

[Frozen static results and audit](../benchmarks/reports/phase5-static-v1.json)
