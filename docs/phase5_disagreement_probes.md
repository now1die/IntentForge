# Discriminating probes

The worker samples up to eight distinct vectors with at most four scalar arguments. It interleaves bounded threshold scans of the candidates, considers both comparison orientations and nearby values, and adds a limited set of paired sign variations and scalar seeds. Simple local-array length hypotheses contribute inputs. Signatures with incompatible types or programs with global state abstain.

Observed values, program faults and per-run execution limits can distinguish pairs. Unsupported outcomes and aggregate-budget exhaustion are reported as incomplete observations. Greedy review prioritization first maximizes previously unseparated pairs, then all separated pairs, boundary evidence and lower measured step cost. The worker keeps the common 200,000-step budget.

The controlled same-pool comparison separated 3/4 pairs with Phase 5 and 0/4 with the legacy generator. The equivalent pair remained unresolved. The fixtures target specific probe behaviors and provide no population estimate. Phase 5 used 432 VM steps across these fixtures, versus 368 for the legacy comparison. In the frozen live set, sixteen probes separated four candidate pairs over two cases at a cost of 264 VM steps. The ambiguous gate case only became a single supplied-test match after the evaluator explicitly specified the first argument as the target.

```sh
python -m pytest -q tests/test_phase5_behavior.py
python -m benchmarks.phase5_evaluate --check
```
