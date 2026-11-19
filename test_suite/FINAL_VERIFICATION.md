# Final compiler verification (current ML-first build)

The current authoritative report is [`ML_FIRST_FULL_SCENARIO_VERIFICATION.md`](ML_FIRST_FULL_SCENARIO_VERIFICATION.md). It replaces historical totals from the earlier fixed ZIP.

## Current measured results

- Repository test suite: **432 passed**.
- General compiler corpus: **220/220 expected outcomes matched**.
- Keyboard/array exact-repair matrix: **65/65 exact, 0 failures, 0 crashes**.
- Stress matrix: **3,758 executions, 0 crashes, 0 wrong-phase results**.
- Model: **20 correction classes**, 1,660 balanced synthetic examples (83 per class), 1,328 train / 332 held-out, with 100% accuracy on the controlled synthetic held-out split.
- All 20 trained classes were exercised end-to-end against a packaged example in the repository tests.

The controlled synthetic accuracy is not a claim of 100% accuracy on arbitrary student code. Parser validation remains mandatory, and ambiguous repairs remain unresolved rather than being guessed. See `docs/ml_correction.md` and the full verification report for scope and limitations.
