# Candidate precision and review burden

Phase 9 confirmed completed output mismatches for 14/18 faulty originals and
raised zero alerts for 18 correct controls. Three other faulty originals gave
runtime failures and one reached its call-depth limit. The verifier retained
the existing distinctions in all three profiles tested.

Of 16 compiler-valid candidates, 13 passed discovery and all 13 passed separate
holdout cases. The other three were speculative hypotheses on one correct
control and were collapsed by default. They were incompatible with its
trusted discovery outputs. The matching original retained those optional
candidate IDs. One faulty case had more than one compatible candidate. Nine
of 38 cases had a recommendation, and 29 had none. All nine recommended
candidates passed holdout.

The same candidate pool gave exact top-1 and top-3 recall of 12/18 in both
deterministic static order and behavior-guided order. The new profile retains
deterministic synthesis order. Its probes had no measured new pair separations
in the final cohort. [Versioned measurements](../benchmarks/reports/phase9-live-v1.json)
