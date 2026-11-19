# Phase 5 execution security

Phase 5 uses the [Phase 4.5 deployment controls](phase4_5_security.md), including the direct loopback gateway, owner-only Unix socket, non-root disposable child, seccomp filter, read-only filesystem, disabled network, process and memory bounds, CPU limits and wall deadline. Hosted execution remains disabled. Full C is analysis-only.

New source analysis shares the token, source, nesting, attempt and deadline bounds. The execution batch keeps five total programs, twelve test vectors, eight probes and one shared 200,000-step VM budget. Threshold discovery visits at most 256 nodes per candidate. Invalid or extraneous bodies are rejected. Responses require matching source fingerprints, entry point, candidate IDs and test vectors. In observation-only mode the gateway rejects any returned test-match evidence. A user cannot send behavioral evidence or substitute executable code for a server-generated candidate.

```sh
python -m pytest -q tests/test_phase45_isolation.py tests/test_phase5_behavior.py
python -m benchmarks.phase45_isolation
python -m benchmarks.phase5_evaluate --live --check
```

Independent public deployment assessment remains pending.
