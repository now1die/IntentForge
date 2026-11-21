# Candidate generation

| Candidate family | Basis |
| --- | --- |
| `RECURSIVE_PARAMETER_PROGRESS` | Static unchanged-argument evidence and modeled guard |
| `RECURRENCE_OPERATOR_MISMATCH` | Typed supplied examples plus structurally bounded operator alternatives |
| `PATH_RETURN_DEPENDENCY` | Supplied examples and cross-path def-use evidence |

Phase 6.5 can add up to six hypotheses to the earlier profiles. The engine shares its compile attempt limit across all categories and deduplicates sources and equivalent candidate ASTs. It rejects conflicting edits and drops compiler-invalid alternatives. Legacy multi-site repair support is covered by regression tests. The final Phase 6.5 cohort produced three code-only and twelve guided compiler-valid candidates, all single-site.

Candidate metadata distinguishes static evidence, supplied examples and supplied expressions. Tests and a compiled alternative are evidence for review. Selecting and applying a repair remains explicit.
