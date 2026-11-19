# ML Generalization 3.0 final review

**Complete with limitations.** The opt-in Mini-C v3 engine improves
bounded, compiler-checked candidate generation and the requirement
grammar. It detects structural conflicts and peer patterns and retains
explicit review for every speculative patch. The versioned artifact
contains three trained models. The held-out selection gate left
learned ranking disabled. Existing models and benchmarks remain
available.

On this 18-reference cohort, Phase 2.5 learned matched 3 at top 1
and generated 4. Full v3 matched 6 and generated 9. Keeping the
candidate pool fixed, v2, v3 pointwise and v3 boosted ordering each
matched 7. No final results entered model selection. The three
external-description adaptations yielded zero correct code-only
matches. Broad generalization and reliable probability calibration
remain unestablished.

The regression suite covers the original API and engine versions,
new bounds and typed permutations, review invalidation, weak-logic
abstention, requirement parsing and artifact fallback. Reproduce with
the commands below after installing the existing Python and frontend
dependencies.

```bash
export OPENBLAS_NUM_THREADS=1
python -m pytest -q
python -m benchmarks.review_corpus
python -m benchmarks.phase2_audit
python -m benchmarks.phase25_audit
python -m benchmarks.phase25_evaluate --check
python -m benchmarks.ml_v3_audit
python -m benchmarks.ml_v3_evaluate --check
python -m test_suite.run_test_cases
python -m test_suite.run_keyboard_and_array_regression --verify
python -m test_suite.stress.run_stress_tests .
npm --prefix frontend run build
npm --prefix frontend test
```

- [Architecture and audit](ml_v3_architecture.md)
- [Model card and training reproduction](ml_v3_model_card.md)
- [Evaluation and ablation](ml_v3_evaluation.md)
- [Data provenance and failure analysis](ml_v3_generalization_analysis.md)
