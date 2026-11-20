# Structural robustness

The trusted fixture replay validates alpha renaming, formatting, return parenthesization, operand reversal in pure comparisons, and swapping adjacent literal initializers. It compares original and transformed compiler validity, VM status and observed values, and checks that every emitted edit span remains inside the transformed source. The replay covers adjudicated faults and known-correct controls. It leaves partial specifications to the ambiguity study.

All 146 transformations preserved the observed behavior. Alerts and candidate categories were consistent in 145/146 transformations. Reversing the orientation of the guard in the nested-marks defect removed the loop hypothesis even though compiler and VM evidence agreed. That is a structural generalization failure.

On the family-exclusive final set, exact candidate recall was 0/3 for faults in a category present in the admitted non-final partitions and 2/16 for other categories. The small denominators distinguish these conditions but provide limited evidence of transfer.

```sh
python -m benchmarks.phase55_evaluate --check
python -m pytest -q tests/test_phase55.py
```

[Case-level transformations and transfer outcomes](../benchmarks/reports/phase55-static-v1.json)
