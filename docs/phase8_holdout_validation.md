# Holdout validation

Discovery vectors are the only expectations sent when generating candidates. Versioned fixture manifests freeze discovery and holdout inputs. The evaluator checks independent reference behavior and verifies every discovery-passing candidate in a separate worker request with candidate generation disabled. It checks candidate source identity and records edit, category, outcome, recommendation and concrete counterexamples.

Nineteen exact candidates and one non-exact alternative passed both sets, for 20/22 passing holdout checks. Two alternatives on the paired-dial case passed discovery and then failed on both independently varied held-out pairs. For input `[3, 7]`, both returned 30 against an expected 36. Neither received a recommendation. No recommended candidate failed its holdout.

The finite-grid case checks every pair in `{0,1,2} × {0,1,2}`, with three discovery and six holdout inputs. The checked-offset case includes both valid endpoints from `INT_MIN` through `INT_MAX−3`. Other domains are case-specific and recorded in the fixture and live reports. Finite agreement describes the checked inputs.
