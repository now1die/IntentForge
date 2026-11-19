# Phase 2.5 candidate ranker

`models/intention_ranker_v2.joblib` is a separate, 12,935-byte repository
artifact with a versioned feature schema. The legacy classifier and
Phase 2 ranker remain available. The new training fit 594 candidate
rows with 102 accepted matches and 576 ordered pair rows derived from
positive/negative alternatives in the same category.

The experiments compare deterministic order, the Phase 2 ranker,
weighted pointwise logistic regression, signed feature-difference pairwise
logistic regression, and 40 depth-2 boosted trees. These estimators suit the
small structured dataset and use the same available candidate pool. The
dataset and resource budget favor these lightweight methods over a neural
encoder experiment.

Features include AST role, scope kind, bound symbol kind, type agreement,
lexically prior reads and writes, parameter-derived initializers,
declaration distance, argument position and formal-name similarity,
index context, comparable peer count, edit shape, and diagnostic change.
They contain program observations rather than runtime def-use proofs.
Program names, mutation IDs, and target labels are excluded. The synthetic
generation intentionally links many correct candidates to prior usage.
That correlation limits how broadly an observed model gain can generalize.

## Held-out model selection

Selection requires improvement over both deterministic ordering and Phase 2
on top-1 count and family-macro accuracy, with at least two validation
families. The deployed learned scope covers compiler-diagnosed alternatives
with the same validity, requirement-support count and category. Pure
logic hypotheses and unselected categories use deterministic ordering.

| Category | Deterministic | Phase 2 | Selected and validation top 1 |
|---|---:|---:|---|
| Variable reference | 2/12 | 6/12 | Pointwise, 12/12 |
| Missing expression | 0/12 | 0/12 | Pointwise, 12/12 |
| Array index | 2/12 | 2/12 | Pointwise, 12/12 |
| Function argument | 2/12 | 2/12 | Pointwise, 12/12 |
| Declaration/type | 0/12 | 0/12 | Pointwise, 12/12 |
| Multiple localized | 2/12 | 2/12 | Boosted, 8/12 |

Across the 72 labeled validation cases, one global pointwise ordering gave
64 top-1 matches, pairwise gave 66, and boosted gave 68. Per-category
selection also gave 68. The separate development test gave 34/36 for the
selected methods. Final results show a much smaller ranking gain.

## Calibration and risks

Validation top-vs-runner-up margins fit exploratory sigmoid and isotonic
calibrators. Separate calibration families check their Brier error and
risk-coverage. Most individual categories had only positive outcomes on
the small fitting set. In the multi-edit category, held-out Brier scores
were 0.222 for the observed-prevalence baseline, 0.111 for sigmoid, and
0.000 for isotonic. This was 12 labeled examples across two closely
related synthetic families. Their repeated margin patterns limit the
result's generality. Its ranked risk counts were 0/3, 0/6, 1/9, and 4/12
as coverage increased. The pooled exploratory results in the training
report combine margins from different estimator families. They do not
establish a common confidence scale.

The application exposes relative margins only. It uses no probability
threshold or runtime confidence calibration. Static evidence and
mandatory approval govern speculative alternatives. [Training and calibration data](../benchmarks/reports/phase25-training-v1.json)
