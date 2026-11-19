# ML generalization analysis

The archived model report records 25 classes and 640/640 correct predictions on
a controlled stratified split with 2,560 training rows. The historical final
verification attributes those 3,200 rows to the original 2,400 generator rows
and 800 scenario rows. This archive contains the 2,400 generator rows and 640
scenario rows. The saved model is preserved. The archived files are sufficient
to inspect template reuse and feature construction, with 160 historical
training/evaluation rows unaccounted for.

## Archived split reconstruction

`python -m benchmarks.audit_training` applies the historical 80/20 stratified
seed-42 procedure to the 3,040 available rows.

| Observation | Result |
|---|---:|
| Reconstructed train / test rows | 2,432 / 608 |
| Test inputs with a normalized corrupted template seen in training | 588/608 |
| Test inputs with a normalized corrected template seen in training | 608/608 |
| Exact corrupted-source duplicates across train and test | 0/608 |
| Distinct corrupted / corrected templates in the archive | 140 / 22 |
| Rows where `strong_pattern` is populated with a class name | 1,956/3,040 |
| Populated `strong_pattern` values matching the target class | 1,956/1,956 |

Template normalization removes identifiers and literal values. Shared templates
persist even though exact corrupt sources differ. The training generator and
scenario generator select templates by mutation label and vary names, values,
and some types. Row-level stratification mixes those variants across partitions.
This is template leakage for an evaluation intended to measure generalization to
new contexts.

`strong_pattern` uses source regexes keyed to particular mutation shapes and
returns the matching repair class name as an input feature. The three
`strong_pattern_*` features repeat the shortcut alongside local context.
Candidate token/action signatures also expose what native recovery has already
considered. These values are available at inference time. The feature extractor
does not directly consume the stored target or expected repair. The label-shaped
patterns are nevertheless a strong shortcut on this synthetic generator. A
features ablation would quantify how much the model relies on them.

## Independent evaluation

The frozen corpus passes normalized-source separation against the available
training files. On the class-labeled subset, the bundled classifier predicts
11/11 classes. The subset is small and consists primarily of repair categories
the model already supports. Hybrid repair matches 10/26 known intended
sources, and 8 specification-level faults pass the compiler undetected. A
compiler-valid candidate for the adjacent-operands case ignores one operand
and fails the requirement to return their sum. The safety gate leaves that
proposal for explicit review. Behavior of unmatched repairs remains unverified.

The evidence supports a narrow role for classification of recognized syntax
patterns. There is no demonstrated generalization to arbitrary intent,
undefined names that require choosing a binding, or wrong-but-valid expressions.

## Proposed Phase 2 evaluation and architecture

Freeze groups by uncorrupted normalized template and mutation family before
splitting. Evaluate a held-out family or independently sourced program as a
group, and freeze a separate final test set. Report measurements at the class,
candidate-generation, ranking, abstention and behavior stages. Compare a
rules-only baseline with the model, a `strong_pattern`-only baseline, and
ablations that remove the pattern and native candidates from features.

Keep compiler diagnostics, candidate generation and ranking separate. Use AST,
scope and type information as inputs to a ranker that can use supplied
specifications and regression examples as evidence. Evaluate an abstaining
ranker on ambiguous alternatives. Add behavior checks only where a trusted
execution or specification oracle exists. Keep candidate review for
behavior-changing choices. This phase leaves the trained artifact and language
scope intact.
