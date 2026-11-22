# Interpolation ambiguity

The two archived alternatives agree on the discovery and archived holdout inputs. One inserts an equal-endpoint guard. The other adds that guard and moves multiplication before division. The static workbench shows both, and the chosen worker strategy adds no expected output.

The same candidate pool had no pair probes in Phase 11. Phase 11.5 checked eight stretched, typed inputs under the existing worker budget and distinguished the pair in two. For example, `[2147483647, 0, 536870911, 1073741823, 2147483647]` exposes a checked overflow for the reordered expression. The pair remains ambiguous and neither preview is promoted on that basis.

A separate diagnostic replay enumerated all four-cell nondecreasing arrays over {-1, 0, 2} and keys -2 through 3, for 90 inputs. Each alternative satisfied an independently computed matching-index or absence contract on 90/90. The candidates returned different valid indexes on two duplicate-key cases, including key 2 over [0, 0, 2, 2], where indexes 2 and 3 both satisfy membership. [Finite domain](../benchmarks/reports/phase115-static-v1.json) · [Bounded worker probes](../benchmarks/reports/phase115-live-v1.json)
