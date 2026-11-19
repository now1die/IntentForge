# Phase 3.5 final review

**Complete with limitations.** This milestone delivers the six scoped
workstreams and preserves historical compiler and benchmark contracts.
Wider ML generalization, public deployment safety, live Ollama and
execution-based correctness remain unverified.

| Workstream | Result |
|---|---|
| A. Recovery and ranking | V4 recovered more bounded-loop references. No learned category qualified for deployment. |
| B. Evidence | Version 1 adapters and shared inspector cover Mini-C and libclang. |
| C. Security | Bounded transport, serialized probe, typed worker output, packaged-model integrity, and a smoke-tested networkless container. |
| D. Abstention | Evidence-based recommendations and held-out empirical risk. V4 exposes no probability. |
| E. Ollama | Bounded adapter and explicit approval for Ollama-assisted alternatives. Live service unavailable. |
| F. Behavioral oracle | Typed trusted evidence and a snapshot check, covered by a fixture executor. |

See the [initial merged baseline](phase3_5_baseline.md),
[architecture](phase3_5_architecture.md),
[ML generalization review](phase3_5_ml_generalization.md),
[Clang integration](phase3_5_clang_integration.md),
[security review](phase3_5_security.md),
[calibration study](phase3_5_calibration.md),
[Ollama verification](phase3_5_ollama.md),
[behavioral oracle contract](phase3_5_behavioral_oracle.md),
[consolidated evaluation](phase3_5_evaluation.md),
[Phase 4 readiness](PHASE_4_READINESS.md), and
[real workbench captures](../audit/phase3_5).

The integrated local suite passed 557 Python tests, including the 24-test
Clang and workstream suite. It passed the frontend production build,
23 Chromium tests, and all 220
original compiler cases, the 65-case keyboard and array verification,
and 3,758 stress inputs. Historical corpus, training and repair decisions
reproduced. Use the workstream documents to replay the new audit and
same-pool ranking study.
