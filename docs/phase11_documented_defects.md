# Archived diagnostic defects

| Case | Root cause and Phase 11 response |
| --- | --- |
| Constant interpolation domain | Equal endpoint values collapse the denominator. The model can insert a supported guard and move multiplication before the quotient. |
| Coprime zero operand | The minimum-bounded trial helper returns zero before a useful divisor test. The model accepts a discovered signed magnitude-one guard for a zero operand. |
| Short rotated-array pivot | The original uses nonexistent neighboring cells and three different interval updates. It remains outside the recognized binary pivot form. |
| Shifted missing member | The halving helper is modeled, but a missing extrema scan and dependent aggregate changes exceed the two-site grammar. |

These are historical diagnostics. They are outside the denominator for fresh documented-defect evaluation. The source and both old and new results are included in the replay report. [Diagnostic report](../benchmarks/reports/phase11-static-v1.json)
