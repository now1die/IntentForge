# Boolean and interval constraints

Boolean projection supports integer comparisons, negation, conjunction and
disjunction. Conjunction and disjunction retain left-to-right short-circuit
evaluation. Synthesis considers comparison strictness, equality polarity,
nearby literals, ordered operand swaps and conjunction/disjunction replacements
where the operands are pure projected terms.

Whole-expression replacements parenthesize their constituent terms to preserve
their AST grouping. Each replacement is compiler validated and must satisfy
the supplied expectations in the static model. The isolated worker observes
the compiled candidate separately.

The relay benchmark represents every point of the declared
`{0,1,2} × {0,1,2}` domain. Four points guide synthesis and five remain sealed for
validation. The result establishes agreement over those nine points for
candidates that pass both partitions.
