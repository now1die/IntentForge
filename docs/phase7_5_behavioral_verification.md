# Behavioral verification

Profile 75 uses the existing isolated Phase 7 worker protocol and verified-original gate. A completed original mismatch is a confirmed fault. Matching originals, runtime errors, execution limits, unavailability and incomplete specifications have separate states. Suggestions remain available without promotion. Review eligibility requires a single candidate matching all supplied tests and a confirmed mismatch in the original.

The final cohort recorded 23 original mismatches, 31 matches and one call-depth stop. Twelve cases received a review recommendation, four had multiple passing alternatives, and 43 had no single recommendation. Sixteen faults had at least one candidate matching the supplied and held-out vectors. Two extra non-exact alternatives passed both suites. One additional alternative on a faulty program and one on a correct control passed discovery and then mismatched on holdout. Neither was recommended.

The worker spent 37,261 supplied-test steps, 20,075 probe steps and 6,569 held-out test steps across the cohort. The existing input-only strategy separated 37 pairs in 156 probes on the larger candidate pool. Each request retains its own shared 200,000-step budget. Probe outcomes never become trusted expectations.
