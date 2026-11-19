# IntentForge Phase 2.5 final review

**PHASE 2.5 COMPLETE WITH LIMITATIONS**

The work starts at merged revision `7b1c09927100518aaae9bb3444f99548f0bd1acd`
and preserves the Mini-C compiler, original classifier, Phase 2 artifact,
Phase 1 approval policy and historical benchmark files. The new engine
adds scoped code-only hypotheses, typed argument placement, bounded
multi-site repairs, an expanded description grammar, and category-local
ranking. Three workbench modes distinguish the evidence supplied by users.
Every changed source still requires explicit approval.

## Ranking, data and generalization

Three lightweight experiments share the same candidate pool. The separate
artifact enables weighted pointwise logistic regression for five categories
and shallow boosting for multi-edit repairs. Pairwise logistic regression
remains a comparator. Validation selection improved over both earlier orders
on synthetic families. Training used 109 cases in 19 families, validation
and calibration each used 73 cases in 13 separate families, development
used 37 in seven, and the frozen final set used 44 cases in 43 families.
Five final cases adapt licensed public task requirements using original Mini-C
source. The complete raw, normalized-token, AST, family, reference and
near-duplicate audit passed without remaining cross-split overlaps.

The code-only final result was **16/30** top-1 and **18/30** top-3. Phase 2
learned was **8/30** and **11/30**. Expanded deterministic ordering was
**15/30** and **18/30**. The enlarged candidate set drove most of the gain.
The learned model gained one final top placement and lost two placements
against expanded deterministic on the historical cohort. It remains scoped
to compiler-diagnosed alternatives. Code-only hypotheses use deterministic
ordering.

On 14 matched logic cases, code-only, natural-language and explicit mode
matched **3/14**, **7/14** and **14/14** respectively. Five unsupported natural
descriptions abstained. Code-only generated logic alerts for **6/18** known
faults and **2/8** valid controls across the full final set. The adapted
exercise subset had **0/5** code-only matches. Results from exact expressions
remain separate from source-only capability.

## Safety, calibration and verification

The model compares candidate margins within valid groups. Held-out
calibration and risk-coverage were evaluated separately from the final
evaluation. The multi-edit calibration test had only 12 labeled cases from
two nearby synthetic families. Scores remain uncalibrated in the application.
All four final ambiguous inputs abstained from automatic change, and none
of the 42 supported final programs was automatically edited. Runtime
verification remains unavailable.

| Verification | Baseline | Phase 2.5 |
|---|---:|---:|
| Python | 508 passed | 526 passed |
| Browser | 16 passed | 18 passed |
| Frontend build | Passed | Passed |
| Compiler verification | 220 passed in prior report | 220 passed |
| Keyboard and array reference repairs | 20 automatic, 45 available for review | Same counts, zero lost references and zero crashes |
| Stress | 3,758 cases in prior report | 3,758 cases, zero crashes and zero expected mismatches |
| Historical Phase 1 and Phase 2 checks | Reproduced | Reproduced |
| Phase 2.5 evaluation | New | Audit passed and deterministic decisions reproduced |

GitHub Actions runs the additional corpus and evaluation checks alongside
Python and browser checks. The pull request records hosted outcomes on the
submitted revision. Four screenshots from the real local workbench document
the updated review surfaces, including mobile.

## Phase 3 readiness

The project has a suitable baseline for isolated behavioral verification
and further research. General source-only inference is still weak, with
missed cases, two benign heuristic alerts, and limited final model lift.
A future phase can measure those weaknesses with a trusted behavioral
oracle and larger independently authored case families. Automatic behavior
changes remain outside the current evidence.

- [Architecture](phase2_5_architecture.md)
- [Training, provenance, and commands](phase2_5_training.md)
- [Model card and calibration](phase2_5_model_card.md)
- [Evaluation and limitations](phase2_5_evaluation.md)
- [API and workbench usage](phase2_5_intention_analysis.md)
- [Fresh screenshot evidence](../audit/phase2_5/README.md)
