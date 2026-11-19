# Intention ranker v3

`models/intention_ranker_v3.joblib` is a separate, 11,528-byte artifact.
It contains weighted pointwise logistic regression, signed-difference
pairwise logistic regression, and 35 depth-two boosted trees. The
training set yielded 52 usable candidates from matching strata, with
17 accepted labels, and 70 directed pair examples. The seed is 7019.
The artifact and training report reproduced byte-for-byte locally.

Features combine lexical block usage, direct writes, AST role,
control depth, symbol kind, type compatibility, diagnostic changes
and edit complexity. The learner excludes raw identifiers, textual
identifier similarity, formal-parameter name similarity, requirement
support, and rule strength. Rules order tiers separately. Learned models
can only reorder comparable compiler-diagnosed alternatives. Runtime
behavior and full reaching definitions are outside the feature contract.

Selection uses independent program families. A category needs at least
three top-1 family wins and no loss over either deterministic or v2
ordering on the identical pool. The one-sided sign-test screening
threshold is 0.125. This is an exploratory gate, and the small
per-category samples do not establish statistical significance.
On nine repair references the deterministic, v2, pointwise and
boosted configurations each got 8/9. Pairwise got 7/9. No category
qualified, so v3 uses deterministic ordering. The workbench and API
retain the Phase 2.5 default and offer v3 as an explicit choice.

On seven calibration references, each experimental ranker provided
comparable top-two margins for five. Selecting the largest one or
three margins gave zero errors, and using all five gave one error.
Deterministic ordering found all seven. Strong evidence had two
samples, each correct. Those counts are insufficient for probability
calibration or a threshold. The UI shows reviewable evidence and
uncertainty. It never exposes confidence percentages.

```bash
OPENBLAS_NUM_THREADS=1 python -m benchmarks.train_ml_v3 \
  --model /tmp/intention-ranker-v3.joblib --report /tmp/ml-v3-training.json
cmp models/intention_ranker_v3.joblib /tmp/intention-ranker-v3.joblib
cmp benchmarks/reports/ml-v3-training-v1.json /tmp/ml-v3-training.json
```

[Training and selection results](../benchmarks/reports/ml-v3-training-v1.json)
