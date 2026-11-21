# IntentForge Phase 8.5 final review

Phase 8.5 adds opt-in engine 85 for branch-sensitive scalar constraints,
coordinated two-site coefficient edits and bounded affine counting repairs.
The workbench shows the supplied specification, sampled paths, loop counts
and both locations of coordinated repairs. It applies a candidate in one
explicit approval. Phase 8 remains available independently.

## Results on the frozen final cohort

| Metric | Phase 7.5 | Phase 8 | Phase 8.5 |
| --- | ---: | ---: | ---: |
| Faults confirmed by supplied tests | 13/14 | 13/14 | 13/14 |
| Confirmed control alerts | 0/14 | 0/14 | 0/14 |
| Exact guided repairs passing holdout | 0/14 | 0/14 | 10/14 |
| Faults with a candidate passing both suites | 0/14 | 0/14 | 11/14 |
| Exact code-only repairs | 0/14 | 0/14 | 0/14 |

Phase 8.5's exact holdout result has a 95% Wilson interval of 45.4% to 88.3%.
It compiled 13 proposals, including three coordinated pairs. All 13 passed
discovery, 12 passed holdout and one failed on two relay-grid inputs. Two
non-exact candidates passed both suites. All nine recommended candidates
passed holdout.

The 13 Phase 8.5 live candidates and original snapshots used 6,795 discovery
steps. Probes used 378 steps and distinguished one previously unresolved pair
across 12 probes. Candidate holdouts used 1,296 steps. On the discovery
requests the largest reported sample used five live cells and one call frame.
Timed measurements include the local gateway and, where applicable, follow-up
holdout requests.

The misses include an original with a fault observable only on holdout,
variable and mixed loop updates, and the archived nested Euclidean predicate.
The cohort has four pinned upstream adaptations, 14 intentionally injected
final faults and no external human adjudication. The [readiness review](PHASE_9_READINESS.md)
records the limits of broader claims.

## Verification and artifacts

- [Merged Phase 8 baseline and workflow results](phase8_5_baseline.md)
- [Architecture and execution boundary](phase8_5_architecture.md) · [Security](phase8_5_security.md)
- [Static ablations, historical diagnostics and robustness](phase8_5_generalization_evaluation.md)
- [Candidate precision and review burden](phase8_5_candidate_precision.md) · [Holdout validation](phase8_5_holdout_validation.md)
- [Corpus provenance](phase8_5_dataset_provenance.md) · [Leakage audit](phase8_5_leakage_audit.md)
- [Workbench and Chromium screenshots](phase8_5_workbench.md)

The full local Python suite passed all 789 tests with the restricted worker.
The historical isolated evaluations passed through Phase 8. The local live
Ollama endpoint was unavailable. `LIVE_OLLAMA_STATUS=NOT_VERIFIED`.
