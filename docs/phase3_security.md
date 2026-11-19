# Clang security

Clang is disabled by default. The app starts Mini-C independently of
any Clang library, Python bindings or Linux seccomp. Enabling Clang
requires operator-controlled `INTENTFORGE_CLANG_MODE=isolated` and an
absolute trusted libclang file path. Keep both unset on the current
Vercel deployment. Capability discovery tests the worker and fails closed.

The parent starts a disposable Python process using an argument array,
a private temporary directory and a minimal environment. There are no
request-defined flags, environment variables, program launches or
filesystem paths. Client file keys are validated before use and source
is provided to libclang as in-memory unsaved buffers. The worker loads
the installed runtime first, then installs a Linux seccomp syscall
allowlist before parsing. No filesystem opens, path metadata queries,
network calls, child processes or executable launches are allowed after
activation. Standard system headers are excluded. The suite exercises
macro-expanded host includes, `__has_include` and C23 `#embed`.
Compiler invocations use syntax-only parsing. There is no linking,
execution, build discovery or Makefile handling.

Limits include a 640 KB body cap, 96 KB of UTF-8 source, 12 files,
four distinct entry points, two active workers per service process, an
eight-second wall timeout, five CPU seconds, 640 MiB address space, a
3 MB output cap and 3,500 AST nodes per unit. Core dumps are disabled.
Worker failure returns a stable status and the parent cleans up the
temporary workspace. Keep the worker user nonprivileged.

For public use, provision and harden a dedicated Linux service with a
read-only image, minimal mounted filesystem, no credentials, no outbound
network, non-root identity, namespace isolation and deployment-level
request quotas. Verify the kernel/container seccomp policy allows the
worker to install and stack its restricted policy. Treat the native
compiler, Python, kernel and container runtime as trusted dependencies.
The application controls reduce exposure and do not constitute a
production security review or deployment verification.
