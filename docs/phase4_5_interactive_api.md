# Interactive behavioral verification API

`GET /v1/behavioral-verification/capability` reports `available`, `disabled`, `unsupported_environment`, `worker_unavailable`, `worker_unhealthy`, `capacity_reached` or `deadline_exceeded`. A verified local service includes boundary `isolated-local-v1`. The static smoke fixture may run on capability discovery.

After starting the [local profile](phase4_5_execution_isolation.md), send a versioned verification request to the main API.

```sh
curl --fail http://127.0.0.1:8000/v1/behavioral-verification \
  -H 'Content-Type: application/json' \
  --data '{"source":"int f(int x){return x+2;}","entry_point":"f","vectors":[{"arguments":[4],"expected":8}],"trace":true,"compare_candidates":true,"return_expression":"x*2"}'
```

The request accepts `language: "mini-c"`, up to 24,000 source characters and 48,000 UTF-8 bytes, a function identifier, 1–12 vectors with up to 16 scalar arguments each, and strict signed 32-bit integer or Boolean values. Options include trace, candidate comparison and an explicit return expression or condition of up to 160 characters. Limits default to 10,000 steps, 32 frames and 4,096 cells, with maxima of 20,000, 64 and 8,192 respectively. Oversized transport bodies return HTTP 413. Invalid JSON or fields return HTTP 422.

The response carries the SHA-256-based program identity, entry point, availability, original BehaviorOracle evidence, static-ranked candidate evidence, a review order, comparison status, observational probes and a mandatory approval marker. Each run carries verification and interpreter status, typed observations and expectations, per-vector outcome, runtime code and location, steps, peak cells, call depth and any requested bounded trace. Unsupported execution is reported in the interpreter result. Infrastructure failure yields an availability response without execution evidence.
