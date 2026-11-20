# Phase 5.5 security

Phase 5.5 leaves the [Phase 4.5 Linux profile](phase4_5_security.md) and worker image protocol in place. The worker continues in a restricted disposable child with no network, read-only container files, syscall restrictions and existing CPU, memory, wall-clock and concurrency bounds. The gateway remains explicit opt-in and direct loopback only. Worker requests have a maximum of four alternatives, twelve supplied vectors, eight probes and the existing shared 200,000-step VM budget.

Static gates use the already bounded Phase 5 scan with at most 1,200 AST nodes, six hypotheses and the original candidate attempt limit. The request schema rejects extra client behavioral data. Source digest, candidate identity, entry point and typed test-vector checks carry forward. The browser invalidates evidence on source or configuration changes and requires explicit approval.

Full C remains analysis-only. Public Mini-C execution remains disabled pending independent assessment. The local and CI verification covers the isolated profile.

```sh
python -m pytest -q tests/test_phase45_isolation.py tests/test_phase5_behavior.py tests/test_phase55.py
python -m benchmarks.phase45_isolation
python -m benchmarks.phase5_evaluate --live --check
python -m benchmarks.phase55_evaluate --live --check
```

[Local restricted setup](phase4_5_execution_isolation.md)
