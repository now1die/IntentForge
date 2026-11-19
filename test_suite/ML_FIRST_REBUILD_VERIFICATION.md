# ML-First Rebuild Verification

This report summarizes the current packaged model rebuild. The controlled synthetic
training/validation accuracy is not a claim of equivalent performance on arbitrary real
programs; see `ML_FIRST_FULL_SCENARIO_VERIFICATION.md` for the full end-to-end test results.

- Model: Scikit-learn `DictVectorizer` + balanced `LogisticRegression`
- Classes: **20**
- Compiler-validated synthetic records: **2,400** (compiler-validated examples)
- Train/test split: **1,328 / 332**, random seed 42
- Held-out accuracy on the controlled synthetic split: **100%**
- The parser validates every accepted correction; semantic cases are also checked by the semantic analyzer.

The active ML classes cover keyboard slips, delimiter/operating-token mistakes, array declarations,
array-indexing versus array-call confusion, missing tokens, extra tokens, operator transpositions,
and keyword spelling errors. The parser also supports comma-separated declarations such as `int a,b;`.

See `docs/ml_correction.md` for the architecture, exact class names, examples, and limitations.
