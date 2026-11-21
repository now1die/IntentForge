# Holdout validation

Guided synthesis receives only the frozen discovery vectors. Every candidate
that passes discovery is resubmitted as an original program snapshot in an
independent isolated request with comparison disabled. The gateway checks
source and vector identities. An exact repair matches the normalized reference
tokens. Behavioral acceptance records supplied and holdout agreement, including
behaviorally equivalent source variants.

The asymmetric grid covers all nine points in `{0,1,2} × {0,1,2}`, split into
four discovery and five holdout inputs. The frozen fixtures preserve each
domain and the exact expected values. Counterexamples from the second request
do not enter candidate generation, classification or selection.
[Frozen cases](../benchmarks/phase9_data/cases-v1.json) ·
[Isolated outcomes](../benchmarks/reports/phase9-live-v1.json)
