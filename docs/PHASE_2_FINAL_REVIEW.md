# IntentForge Phase 2 final review

**PHASE 2 COMPLETE WITH LIMITATIONS**

Phase 2 adds a read-only intention analyzer, scoped candidate generation,
a separately trained candidate ranker, and reviewable, compiler-checked
explanations in the existing workbench. The baseline is merge commit
`4923db21ffdaef3d7c15b6712ceba7b1fec047ba`, which includes Phase 1.5
pull request #1. The Mini-C compiler, original classifier, correction
contracts and prior benchmark evidence are preserved.

## Architecture and model

The new path joins AST edges, source spans, scope and compiler types with
diagnostics and optional requirements. It proposes and validates bounded
local edits, groups comparable candidates and explains what evidence
supported each change. The versioned FastAPI endpoint and React Intention
tab expose the same output. The existing editor only changes after the
user selects a compiler-valid candidate and explicitly applies it.

Weighted logistic regression was selected over shallow boosting on five
validation families. The logistic ranker moved the accepted candidate into
first place on 44/50 cases, versus 41/50 for boosting and 5/50 for
deterministic contextual ordering on the same candidate pool. Training
used 100 reference-mutation programs in ten separate families, producing
290 labeled candidates. It used no historical or final-cohort fit inputs.
Normalized input and reference templates, grouped splits and cross-split
near-duplicates passed the separation audit. The model is used only for
compatible return bindings. Compiler validation and review remain required.

## Outcome

| Cohort | Original hybrid top 1 / top 3 | Context learned top 1 / top 3 | Full intention top 1 / top 3 |
|---|---:|---:|---:|
| Historical, 111 cases | 25/88 / 25/88 | 36/88 / 38/88 | 36/88 / 38/88 |
| Frozen final, 32 cases | 0/19 / 0/19 | 6/19 / 9/19 | 16/19 / 19/19 |

The independent generator found accepted final candidates in 9/19 cases
without user requirements and 19/19 with requirements. Learned ordering
alone moved final top-1 from 5/19 to 6/19 and historical top-1 from
37/88 to 36/88. The stronger full outcome reflects the expanded candidates
and supplied requirements as well as ordering. The model's broader effect
remains mixed.

The full engine flagged all 9 supplied structural logic mismatches, with
0/7 specification alerts on controls and one benign heuristic alert.
All three final ambiguous cases abstained from automatic edits. Restricting
review to strong specified evidence measured 10/19 coverage and 10/10
reference matches. Relative scores are uncalibrated. No runtime behavior
was executed or inferred from compilation.

## Verification

| Check | Baseline | Phase 2 |
|---|---:|---:|
| Python suite | 477 passed | 508 passed |
| Browser workflows | 14 passed | 16 passed |
| Type checking and production build | Passed | Passed |
| Compiler suite | Phase 1 recorded 220 passed | 220 passed |
| Keyboard and array fixtures | Phase 1 recorded 20 automatic and 45 available for review | Same counts, zero lost repairs and zero crashes |
| Stress suite | Phase 1 recorded 3,758 cases | 3,758 cases, zero crashes and zero expected mismatches |
| Historical corpus verification | Baseline reproduced | 111 cases checked with reproducible decisions |
| Phase 2 split and decision check | Unavailable in baseline | 182 cases across training, validation and final splits passed audit, both evaluation cohorts reproduce |

The new tests cover scoped and shadowed references, supported and incomplete
ASTs, spec matching and ambiguity, candidate validation and deduplication,
model fallback and deterministic scoring, bounded input, and approval behavior.
The GitHub Actions benchmark job includes the new corpus and report checks.
The pull request records hosted checks for the submitted revision.

## Remaining limits

General natural-language intent, arbitrary valid-but-wrong logic, and
execution-backed equivalence remain open. The supported wording is bounded,
and the ranker was trained in a narrow binding-repair regime. The final
cohort is newly authored and small, so the numbers support repeatable
comparison within the project. Live Ollama is unnecessary for this feature
and the final evaluation is offline.

- [Architecture](phase2_architecture.md)
- [API and workbench usage](phase2_intention_detection.md)
- [Model card and training commands](phase2_model_card.md)
- [Evaluation and limitations](phase2_evaluation.md)
- [Machine-readable results](../benchmarks/reports/phase2-evaluation-v1.json)
