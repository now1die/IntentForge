# Candidate recovery and ranking

V4 adds ascending and descending integer counted loops with literal starts
and bounds. It identifies direct accesses in the first body statement,
checks the binding and declared array extent, and abstains on possible
counter writes or early exits. It can tighten an inclusive boundary by
one step, remove a unit index offset across a full sweep, or combine one
pair drawn from distinct loops. The same compiler validation, bounded
candidate enumeration, and final approval apply. The generator does
not attempt symbolic loop invariants, interprocedural reasoning or
behavior inference for arbitrary accumulators.

The frozen v3 report had 12 missed top-1 references and one false
positive. The v4 evaluator records each failure and a reason. Older
labels and corpora are replayed without relabeling. Three v3 references
were available below top rank. Nine had no accepted candidate. The
common missing evidence was a precise requirement for boundary
semantics, negation, same-type argument order, or intended arithmetic.

V4 trained pointwise logistic, pairwise logistic and shallow boosted
ranking on 29 candidate rows with 10 positives and 38 directed pairs.
Lexical scope compatibility, candidate counts and edit size supplement
the previous AST, binding, and diagnostic features. The trained
artifact and report reproduced byte-for-byte locally. Category gates
compare over the deterministic and strongest historical ordering on
held-out selection families. Boosted and v2 tied at 5/5 there.
Pointwise, pairwise, v3 and deterministic each scored 4/5. The gate
activated no v4 category. Per-category observations are too sparse for
separately fitted category-specific estimators.

The 13 training, five selection, seven calibration, two development,
and 18 final cases each have distinct families. Exact source,
normalized tokens, normalized AST, and near-duplicate checks at 0.94
include historical corpora and references. The final corpus and code
were committed before evaluation. Two final programs use original
Mini-C implementations adapted from MIT-licensed Exercism descriptions.
The fixture records exact task and license URLs. No independently
collected blind cohort was available.

Four final logic cases raised alerts. Three produced the top reference.
The two-site case produced plausible alternatives, but the fixed
one-pair budget missed the annotated pair. Both external tasks required
algorithm evidence absent from their code-only inputs and scored 0/2.
This supports the narrow array-loop recovery rules and leaves wider
generalization unestablished.
