# Phase 2.5 data and training

All development programs use project-authored references and deterministic
mutations. Multiple scoped candidates can compile, including similarly named
decoys, bindings of the same type, and combinations across two diagnostic
locations. Explicitly ambiguous samples carry no reference label and are
excluded from fitting and calibration. Families combine a control-flow
scaffold with a distinct repair role or program template. Variations within
a family share structure, so case count exaggerates statistical independence.

| Partition | Cases | Program families | Purpose |
|---|---:|---:|---|
| Training | 109 | 19 | Fit feature vectorization and ranking parameters |
| Selection validation | 73 | 13 | Select methods per category, fit exploratory calibration |
| Calibration holdout | 73 | 13 | Measure calibration and margin risk on different families |
| Development test | 37 | 7 | Debug features, generation and evaluation harness before freeze |
| Final | 44 | 43 | Compare the frozen engine and learned artifact |

The final cohort contains 39 project-authored cases and five original
Mini-C solutions adapted from licensed public exercise requirements. The
cohort was constructed after the engine freeze. Case construction is
visible to the project author, and this evaluation has no external grader.
The five independent task descriptions informed the problem requirements.
All Mini-C source and mutations were written for this project.

| Adapted task | Adaptation |
|---|---|
| [Leap](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/exercises/practice/leap/.docs/instructions.md) | Gregorian divisibility on positive integer years |
| [Grains](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/exercises/practice/grains/.docs/instructions.md) | Single-square doubling loop, capped at square 24 for signed integers |
| [Difference of Squares](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/exercises/practice/difference-of-squares/.docs/instructions.md) | Difference of two integer aggregates using a bounded loop |
| [Triangle](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/exercises/practice/triangle/.docs/instructions.md) | Validity predicate for positive integer sides, with inclusive triangle inequalities |
| [Darts](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/exercises/practice/darts/.docs/instructions.md) | Circle scores using integer coordinates and squared radii |

The exercise repository is distributed under the MIT license. Copyright
(c) 2021 Exercism. [Pinned license](https://github.com/exercism/c/blob/1675b02c310198e9752e516ee1a2294b76a37f84/LICENSE)

The audit checks raw source, identifier- and literal-insensitive tokens,
binding-independent AST shapes, family membership, reference compiler
validity, and cross-split input/reference four-gram similarity at
`0.94`. It compares with the archived classifier training data, historic
benchmarks, and Phase 2 training, validation and evaluation data. One
development ambiguity fixture was replaced after a historical template
collision. The deliberate outlier and valid asymmetry control share one
final family. The final audit found zero remaining cross-split exact,
normalized AST or near-template overlaps. Historical sources absent from
the archive and unmodeled semantic similarities remain outside the audit.

## Reproduction

```sh
python -m benchmarks.phase25_data
python -m benchmarks.phase25_audit
python -m benchmarks.train_phase25
python -m benchmarks.phase25_evaluate --development --out /tmp/intentforge-p25-dev
python -m benchmarks.phase25_evaluate --out /tmp/intentforge-p25-eval
python -m benchmarks.phase25_evaluate --check
```

Training only reads development data. The committed training report records
seed 2517, artifact and data digests, scikit-learn environment, training
times and category results. Rebuilding the evaluation excludes elapsed
times from its consistency comparison. [Training report](../benchmarks/reports/phase25-training-v1.json)
