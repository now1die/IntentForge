# Phase 7 baseline

Phase 7 starts at `7bf0846f258f8aeedf9a4b4c4889b7d4e634d282`, the fetched default branch and verified merge of [PR #12](https://github.com/now1die/IntentForge/pull/12). The local baseline passed 721 Python tests with two restricted-worker skips and 30 Chromium tests with seven restricted-worker skips. The frontend built successfully.

| Post-merge workflow | Result |
| --- | --- |
| [Clang analysis](https://github.com/now1die/IntentForge/actions/runs/44892129166) | Passed |
| [Python](https://github.com/now1die/IntentForge/actions/runs/44892129209) | Passed, optional Ollama skipped |
| [Benchmark validation](https://github.com/now1die/IntentForge/actions/runs/44892129220) | Passed |
| [Frontend](https://github.com/now1die/IntentForge/actions/runs/44892129215) | Passed |
| [Isolated Mini-C](https://github.com/now1die/IntentForge/actions/runs/44892129141) | Passed |

The archived Phase 6.5 results reported 5/6 guided exact repairs, 4/13 guided false alerts, six robustness changes out of 124 comparisons, and zero additional pairs separated in sixteen final-cohort probes. Phase 7 replays the known failures and evaluates unfamiliar cases separately.
