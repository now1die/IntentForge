# Phase 6 security boundary

The standard API process performs compiler and static analysis only. Live verification remains behind the direct loopback gateway and owner-only Unix socket. It uses the existing Linux worker with a disposable non-root child, a restricted seccomp profile, a read-only root filesystem, no network, and bounded CPU, memory, wall time and concurrency. The service still limits comparison to four alternatives and shares the existing 200,000-step budget across runs and probes.

Phase 6 maps to the existing private protocol. The gateway verifies source identity, candidate IDs, typed test vectors and entry point before attaching observations. Clients cannot supply observed output or candidate programs. The browser invalidates review on changes to source, profile, inputs, limits or selected entry and applies an edit only through an explicit user action on the current snapshot.

Full C remains analysis-only. Public Mini-C execution remains disabled pending an independent assessment of the target deployment.

```sh
python -m pytest -q tests/test_phase45_isolation.py tests/test_phase6.py
python -m benchmarks.phase45_isolation
python -m benchmarks.phase5_evaluate --live --check
python -m benchmarks.phase55_evaluate --live --check
python -m benchmarks.phase6_evaluate --live --check
```

[Restricted profile setup](phase4_5_execution_isolation.md)
