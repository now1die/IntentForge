# Phase 9 generalization evaluation

The same family-separated final corpus of 18 faults, 18 paired controls and
two incomplete specifications was used for every profile. All configuration
and ranking choices preceded final scoring. Code-only exact recall was 0/18
in every profile.

| Static ablation | Exact guided repairs |
| --- | ---: |
| Phase 7.5 | 0/18 |
| Phase 8.5 | 3/18 |
| Phase 8.5 plus loop normalization | 3/18 |
| Normalization and variable steps | 5/18 |
| Normalization and mixed scalar transfers | 6/18 |
| Phase 8.5 plus runtime projection | 5/18 |
| Phase 8.5 plus cross-branch pairs | 5/18 |
| Combined Phase 9 | 12/18 |

The combined exact guided 95% Wilson interval is 43.7% to 83.7%.
Sixteen submitted candidates compiled. Ten used new categories, including six
generalized loop hypotheses, two runtime constraint repairs and two
cross-branch pairs. Normalization also restores the four archived cases
documented in the robustness report. The expanded 242 sampled transformations preserved candidate categories and
observed candidate effects over the supplied input points.

The isolated report describes accepted alternatives, controls, counterexamples,
ranking and worker costs. The provenance table distinguishes injected faults
from adaptations of documented defects.
[Static measurements](../benchmarks/reports/phase9-static-v1.json) ·
[Isolated measurements](../benchmarks/reports/phase9-live-v1.json)

```bash
python -m benchmarks.phase9_audit
python -m benchmarks.phase9_evaluate --check
python -m benchmarks.phase9_evaluate --live --check
```
