# Candidate precision

On 22 final cases, the isolated original produced three confirmed mismatches, five runtime failures, one execution limit and thirteen agreements. Confirmed alert precision was 3/3 and recall was 3/9. No correct control raised a confirmed alert, produced a speculative candidate or added visible review work (0/13 for each). All six emitted candidates were compiler-valid. No final case had multiple discovery-passing candidates.

The worker recommended 2/22 cases and abstained from recommending 20/22. No runtime or limit result was treated as a trusted output mismatch. Both recommended candidates passed holdout. The same six-candidate pool produced exact top-1 and top-3 recovery of 5/9 before and after behavioral ordering, so this cohort provides no measured ranking gain. Wilson 95% intervals and per-case outcomes are in the reproducible report. [Isolated results](../benchmarks/reports/phase10-live-v1.json)
