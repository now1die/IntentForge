# Calibration and abstention

Five calibration families had reference repairs and two were
controls, including an ambiguous case. All three experimental rankers
provided comparable top-two margins on four of five repair cases.

| Experimental ordering | Errors at top margin | Errors retaining two | Errors retaining all four |
|---|---:|---:|---:|
| Pointwise | 0/1 | 0/2 | 0/4 |
| Pairwise | 0/1 | 0/2 | 1/4 |
| Boosted | 0/1 | 0/2 | 0/4 |

The evidence policy recommended one of seven calibration cases
with zero reference errors. The top candidate existed in six cases.
Five had compiler-confirmed evidence, yet two top candidates missed
the accepted reference. The one strong contextual candidate matched.
These counts do not support stable score thresholds, per-category
calibrators, Brier estimates or reliability plots for probabilities.
The table reports empirical risk and coverage without a probability
claim or a score-dependent deployment decision.

The v4 UI shows specification-supported evidence, a compiler-confirmed
issue, strong or weak context, ambiguity, and unverified behavior.
The recommendation abstains on ambiguous, weak, invalid, or missing
candidates. Review remains available where justified. All edits
still require approval. Final evaluation recommended 3/18 cases,
all top-reference matches. The other 15 inputs abstained.
