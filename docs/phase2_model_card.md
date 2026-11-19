# IntentForge intention ranker v1 model card

The `models/intention_ranker_v1.joblib` artifact uses weighted logistic
regression over a scikit-learn `DictVectorizer`, with seed 2081 and
`C=1.0`. It ranks compiler-validated, competing local or parameter bindings
in return-value positions with equivalent specification and diagnostic status.

The legacy 25-class classifier is unchanged. This artifact is separate and
uses a fixed repository path. A missing, unreadable, incompatible, or
disabled artifact yields deterministic candidate ordering.

## Data and feature provenance

The reproducible generator authored reference programs and changed one return
binding. It produced 100 training cases in ten program families and 50
validation cases in five separate families. The training generator emitted
290 candidate rows, with 100 positives based on accepted reference tokens.
It varied identifiers and values within families. Many corruption spellings
favor a decoy, giving the study a concrete way to measure whether prior usage
and scope help ranking.

The feature schema records AST node and edge shape, binding kind, type
agreement, declaration proximity, prior use of the same binding, text
similarity, edit count and size, and compiler diagnostics removed or
remaining. A requirement-support flag is available for pipeline ordering.
The model received candidate features from training families only. It
has no mutation-class feature, source template identifiers, or known-answer
feature. The learner's application scope follows the training data.

The split audit checks family membership, normalized whole-program inputs and
accepted references against both older corpora, and cross-split input
near duplicates at 0.94 normalized four-gram similarity. No overlaps
remained in the scored data. A proposed final switch fixture was excluded
before scoring because it reused a historical normalized template. The frozen
final cases were authored in this project and are development-independent
with respect to fitting and model selection. They do not substitute for
an externally collected blind sample.

## Selection on validation families

| Ranker | Top 1 | Top 3 | Correctly ordered positive/negative pairs |
|---|---:|---:|---:|
| Deterministic contextual order | 5/50 | 50/50 | 30/100 |
| Weighted logistic regression | 44/50 | 50/50 | 94/100 |
| Depth-2 gradient boosting, 40 trees | 41/50 | 50/50 | 91/100 |

Weighting compensates for unequal candidate classes. Logistic regression
won family-macro top-1 and ordered more validation pairs. The activation
gate also required improvement over deterministic top-1 and family-macro
top-1. In the recorded environment, average inference for ordering one
validation case was about 0.17 ms for logistic regression and 0.25 ms for
boosting. These timings isolate ranking from compiler validation.

The margin is a relative score. Probability calibration was not evaluated.
Closely related variations within the validation families limit statistical
claims. The historical corpus recorded a one-case top-1 loss with learned
ordering, and the new corpus recorded a one-case gain against deterministic
context ranking. The model is intentionally scoped to its validation regime.

## Reproduction

Use the existing dependencies and Python 3.12.

```sh
python -m benchmarks.phase2_data
python -m benchmarks.phase2_audit
python -m benchmarks.train_intention_ranker
python -m benchmarks.phase2_evaluate --check
```

The [training JSON](../benchmarks/reports/phase2-training-v1.json) records data
and artifact hashes, selected parameters, feature definitions, environment,
validation metrics, and timing samples. Training reads the development corpus.
The evaluation command checks persisted review decisions while excluding
clock measurements. Historic reports remain in their original files.
