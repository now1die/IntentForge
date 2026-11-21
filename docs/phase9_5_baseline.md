# Phase 9.5 baseline

[Phase 9 PR #17](https://github.com/now1die/IntentForge/pull/17) merged into
`phase-1-intention-benchmarking` at `6e3a6eec6a847e5ae71abc3c06871d5791072ba4`.
The fetched tip matched the merge. The feature branch starts at that commit.

| Post-merge workflow | Outcome |
| --- | --- |
| [Python tests](https://github.com/now1die/IntentForge/actions/runs/44935384523) | Passed, optional live Ollama skipped |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44935384678) | Passed |
| [Frontend tests](https://github.com/now1die/IntentForge/actions/runs/44935384555) | Passed |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44935384534) | Passed |
| [Isolated Mini-C execution](https://github.com/now1die/IntentForge/actions/runs/44935384508) | Passed |

The local baseline reported 795 Python passes and ten skips, and 38 Chromium
passes and 13 skips in the hosted configuration. The frontend build passed.
Phase 9 produced 12/18 exact holdout repairs from injected faults and 0/3
repairs on documented adaptations. Its 242 sampled transformations preserved
candidate effects. The older results are preserved, with their real cases
replayed separately as historical diagnostics.
