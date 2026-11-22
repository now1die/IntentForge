# Archived documented defects

| Archived Phase 10 gap | Phase 10.5 diagnosis |
| --- | --- |
| Duplicate lower bound | The equality return preempts interval refinement. Removing it and admitting equality into the left branch recovers the reference. |
| Short rotated-array pivot | The original checks nonexistent neighbors and has three update branches. The bounded rotation model abstains. |
| Zero-input LCM | The denominator helper returns zero when both inputs are zero. Independently supplied single-zero expectations and nonzero agreement justify the two-parameter guard. |
| Shifted missing member | The helper's halving progress is established. Recovery would also need a missing scan and dependent range, seed and index edits. |

These samples revisit known behavior. They are excluded from the independent generalization denominator.
