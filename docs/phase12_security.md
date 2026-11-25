# Execution and approval boundary

Phase 12 adds static evidence and a public profile selector. The private protocol stays on version 8. The existing API exposes analysis, while interactive execution requires the local gateway and owner-only worker socket directory. The worker remains non-root, without networking, read-only and capability-free, with default seccomp and additional syscall restrictions, memory, process, concurrency, wall-time and VM step caps.

Locally the worker ran as UID 1000 with an owner-only socket directory, one CPU, 512 MiB of memory, 48 processes and dropped capabilities. The shared VM request ceiling is 200,000 steps. The largest fresh suite in the Phase 12 isolated report consumed 2,028 discovery and probe steps and used 16 peak cells. Public execution is disabled and Full C stays Clang analysis-only. Manual approval compares source identity and applies the entire edit set together. [Execution policy](./PHASE_11_5_FINAL_REVIEW.md)
