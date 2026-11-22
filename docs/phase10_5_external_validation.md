# Independent documented defects

| Upstream fault | Original symptom | Phase 10.5 holdout result |
| --- | --- | --- |
| Python binary search leftmost match | Returns a later equal cell | Guarded adjacent refinement passes all discovery and holdout inputs |
| JavaScript coprime zero operand | Returns false for an operand of magnitude one paired with zero | No candidate |
| Java interpolation over a constant interval | Division by zero | Unsupported loop and array-valued divisor |

The Python repair scans adjacent equal cells after the hit. The pinned fix remembers the hit and refines the binary search, so the alternative earns behavioral credit. Across the three documented defects the acceptable rate was 1/3 (Wilson 95% interval 6.1%–79.2%) and exact recovery was 0/3 (0%–56.2%). The injected faults and archived diagnostics have separate denominators.

Independent executable expectations were used for each numeric domain. External human review was unavailable. [Upstream replay](../benchmarks/reports/phase105-upstream-v1.json) · [Isolated outcomes](../benchmarks/reports/phase105-live-v1.json)
