# Candidate precision

The worker observed two completed-output mismatches, four runtime failures and one execution limit across seven faults. Confirmed-alert precision was 2/2 and confirmed recall was 2/7. All ten correct controls agreed with their expected outputs, with zero confirmed alerts, speculative candidates or initially visible suggestions.

All seven emitted candidates compiled and passed discovery and holdout. Two out of seventeen cases received a recommendation and fifteen did not. Both recommendations passed holdout. The interpolation case had two passing alternatives, so the cohort records one ambiguous case. Static and behavioral top-1 and top-3 exact recovery each measured 4/7 on the same candidate pool. [Precision, denominators and Wilson intervals](../benchmarks/reports/phase11-live-v1.json)
