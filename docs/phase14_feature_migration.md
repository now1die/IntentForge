# Feature migration

Development starts at Phase 13 merge `2e31ca3e538a1b48f9325233026a457db68ff345`. PR #24 was merged and the five baseline workflows succeeded. [Baseline Actions](https://github.com/now1die/IntentForge/actions?query=branch%3Aphase-1-intention-benchmarking)

| Existing capability | Product destination |
| --- | --- |
| Monaco, edit/reset, Mini-C and optional Clang language selection, keyboard editing, backend health | Shared source and connection controls |
| Lexical, syntax and semantic checks, source-linked diagnostics, tokens, AST, scoped symbols | Compiler and Explore Analysis |
| Compiler-generated fixes, option validation, ranking, provider details, custom repair, atomic approval | Compiler Fixes and technical repair summary |
| Static intention analysis, example-based repair, explicit expressions, limited interpreted requirements, input domains and partial inputs | Intention and its advanced settings |
| Runtime tests, compare candidates, traces, resource limits and probes | Test Behavior and Research Lab |
| Historical engine profiles, intention evidence, ML ranking, Clang evidence and recorded demonstrations | Research Lab and its historical workbench |
| Curated examples and source snapshots | Examples & Learning and shared source |

Frontend requests reuse `/health`, `/analyze`, `/tokens`, `/ast`, `/symbols`, `/correct`, `/correction-options`, `/validate-correction`, `/v1/c-analysis`, `/v1/compiler-evidence`, `/v1/intention-analysis` and `/v1/behavioral-verification`. The default workflow uses existing profile 13. Static and worker requests keep their respective existing input schemas. Historical profiles, the classic workbench and their regression tests remain available.
