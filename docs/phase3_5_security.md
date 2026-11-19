# Isolation and production status

**Production deployment and independent security assessment are unverified.**

The worker still receives only validated in-memory buffers inside a private
temporary directory. Linux seccomp denies filesystem paths, networking and
program launches during parsing. Only trusted operator configuration
selects libclang. The body reader rejects compression and caps the stream.
A cold probe is serialized, two analysis slots bound concurrent workers,
worker output has a byte cap and typed shape, and failure terminates the
worker group and cleans the staging directory. Core dumps are disabled.
Native memory, CPU, AST-node, file and source limits remain in force.

The API hashes the exact bytes of bundled model artifacts before
deserialization. Missing or mismatched artifacts fall back to existing
unavailable or deterministic behavior. Explicit CLI training utilities
remain for trusted local artifacts. Hashing is a deployment integrity check.
Write permission to the application and its digest manifest remains trusted.

Tests cover oversized and compressed bodies, malformed output, worker slot
reuse, temporary cleanup, bad paths, blocked host headers, missing libraries,
bad versions, timeout, output exhaustion, cold-probe contention and rejected
artifact bytes. Responses use stable summaries for worker failures and
avoid echoing submitted bodies in transport errors.

For public deployment, keep Vercel on its existing Mini-C path and place
Clang in a dedicated service with non-root execution, read-only image,
isolated tmpfs, no credentials, no egress, restricted mounts and
deployment-level CPU, memory, concurrency and bandwidth limits. Verify
the runtime supports stacking seccomp and map failures to unavailable.
The native toolchain, Python, host kernel and deployment runtime still
form the trust boundary. No restricted public deployment was verified.

## Dedicated service smoke test

The optional `deployment/clang.Dockerfile` includes only the Clang route
and its dependencies. It uses a non-root UID and a Unix socket for an
operator-controlled gateway. The following runs a local networkless
smoke test. Use a named BuildKit `pip_ca` secret if the build environment
requires an organization CA for Python package downloads.

```bash
docker build -f deployment/clang.Dockerfile -t intentforge-clang:local .
container=$(docker run -d --network none --read-only --cap-drop ALL \
  --security-opt=no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777 \
  --memory 1600m --memory-swap 1600m --cpus 1 --pids-limit 32 intentforge-clang:local)
docker exec -i "$container" python - < deployment/clang_smoke.py
docker rm -f "$container"
```

The local smoke test passed with libclang 19.1.7, UID 10001, networking
disabled, a read-only root filesystem, all capabilities dropped and
no published ports. It verified AST output for a C function, denial
of a host include and absence of the main API health route. The
container was removed afterward. A public gateway, deployment quotas,
and independent security review remain unverified.
