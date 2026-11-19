# Correction safety audit

Phase 1 considered some single delimiter insertions low risk after local
parser validation. Delimiters can redirect a body, alter index grouping,
introduce an empty statement, or move a return outside a loop. Phase 1.5
adds token-boundary checks on the validated proposed source. The original
Mini-C grammar and public API shape stay the same.

## Decisions

| Category | Evidence |
|---|---|
| `LOW_RISK_STRUCTURAL` | A standalone single delimiter lands at a limited lexical boundary and its targeted compiler check succeeds. The orchestrator's existing thresholds and ambiguity checks still apply. |
| `AMBIGUOUS` | Distinct repair alternatives survived the available candidate checks. |
| `POTENTIALLY_BEHAVIOR_CHANGING` | The edit replaces/deletes tokens, performs a compound edit, or might alter grouping, scope, arguments or control flow. |
| `UNVERIFIED` | The target validation or the inserted token's boundary could not be established. |

A semicolon is eligible before an explicit statement starter, a declaration
keyword, or a block closer, outside an open parenthesis and after a completed
statement. A closing parenthesis needs a matching control opener immediately
before a braced body and cannot close an inner expression. An index closer
needs a single unmatched bracket and an expected following boundary. An EOF
brace is eligible only for one remaining opener with no intervening nested
block. These rules are deliberately narrow. They establish where the edit
lands and whether it addresses the compiler's target. They do not establish
behavioral equivalence, programmer intent, semantic correctness of a partial
recovery, or uniqueness outside the candidate search budget.

An explicit user approval path remains available. API history retains the
candidate, source span, validation and safety reason. Operator corrections,
identifier replacements and certain delimiter repairs remain reviewable.
The workbench can display the proposed code and continue to accept explicit
edits. Offline comparisons request real correction options without enabling
Ollama transport.

## Measured effect

The comparison runs the Phase 1 safety implementation and the hardened
implementation over the same 111 sources, using the same model, compiler
and evaluator. The new evaluation adapter enabled the measurement on both
trees. The [comparison JSON](../benchmarks/reports/phase1-v2-policy-comparison.json) records the matched dataset and model digests and the changed output.

| Hybrid measure | Phase 1 policy | Hardened policy |
|---|---:|---:|
| Faulty cases with automatic edits | 12/95 | 11/95 |
| Total automatic edit operations | 12 | 11 |
| Cases requiring explicit review | 24/95 | 26/95 |
| Flagged for review with no automatic edit | 24/95 | 26/95 |
| Ambiguous cases left unchanged | 6/7 | 7/7 |
| Reference-equivalent options visible in the workbench | 28/88 | 28/88 |

The differing automatic output was `v2-ambiguous-loop-return`. Appending
a brace at EOF compiled, but it chose whether a return executes inside
the loop. It is now a review-required proposal. No provider rejection was
observed in the offline run. False-safe and false-risky rates have no
behavioral oracle denominator. Reference contradictions are reported
separately from those rates.

The adversarial suite covers nested grouping, empty controlled statements,
for-header separators and nested loops, index precedence, early returns,
identifier changes, assignment versus comparison, and multiple alternatives.
The keyboard/array suite found 20 exact automatic results and 45 expected
reference candidates still available for review. The strict regression
command fails if an expected reviewed repair is only available in the
historical simulation, is missing, or crashes.
