# Phase 4.5 security boundary

| Layer | Implemented control |
| --- | --- |
| Language | Compiler-validated Mini-C AST with integer and Boolean semantics. No native code generation, host functions, I/O, dynamic Python evaluation or arbitrary C execution. |
| Interpreter | Bounded source, arguments, vectors, steps, frames, logical cells and trace. One aggregate 200,000-step budget covers original, alternatives and generated probes. |
| Worker process | Disposable non-root child with an allowlisted seccomp filter, 192 MiB address space, 2-second soft and 3-second hard CPU limits, 3-second wall deadline, output cap and process-group cleanup. The filter is installed before reading submitted messages. |
| Service | Read-only root filesystem, isolated network namespace with loopback only, no capabilities, no-new-privileges, bounded scratch, two worker slots and an owner-only Unix socket. The image contains execution and parsing dependencies and receives no application credentials. |
| Gateway | Explicit local opt-in, Linux, direct loopback peer and local Host and Origin validation. Forwarding headers and socket symlinks are rejected. The private socket and enclosing directory must be owned by the gateway UID and private. |
| Independent review | External security assessment and public deployment authorization are pending. Interactive execution is disabled on the current public profile. |

The service verifies UID, effective capabilities, no-new-privileges, seccomp mode, read-only root, interfaces and kernel resource limits. If finite cgroup memory, process and CPU quotas are unavailable, the controller requires a 384 MiB address-space limit and a 48-process limit, with child CPU limits enforced separately. The local Docker run exercised this fallback because the visible parent cgroup did not contain the requested quotas.

The trusted readiness fixture confirms that the child can execute Mini-C and gets permission errors when it attempts file opening and socket creation. Unit tests simulate deadline, crash and invalid output to verify cleanup and subsequent recovery. The live test verifies the deployed local boundary. Filesystem ownership and the expected service marker establish local service identity. Processes under the same UID are part of the trusted computing base. Deploy the gateway directly on loopback with proxy-header interpretation disabled.

Container and automated checks exercise specific controls. Kernel vulnerabilities, dependency compromise, abuse across tenants, remote identity, per-tenant rate limits and operational monitoring require separate assessment before any public use.
