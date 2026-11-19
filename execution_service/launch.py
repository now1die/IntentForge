"""Private service entry point. Install actual self-limits before serving."""
import os
from pathlib import Path
import resource


def clamp(resource_id, maximum):
    soft, hard = resource.getrlimit(resource_id)
    ceiling = min(hard, maximum) if hard != resource.RLIM_INFINITY else maximum
    target = min(soft, ceiling) if soft != resource.RLIM_INFINITY else ceiling
    resource.setrlimit(resource_id, (target, ceiling))


def verified_cgroup(path=Path("/sys/fs/cgroup")):
    try:
        quota, period = (path / "cpu.max").read_text().split()
        return (0 < int((path / "memory.max").read_text()) <= 512 * 1024**2
                and 0 < int((path / "pids.max").read_text()) <= 48
                and 0 < int(quota) <= int(period))
    except (OSError, ValueError):
        return False


def configure_limits():
    clamp(resource.RLIMIT_AS, 384 * 1024**2)
    clamp(resource.RLIMIT_CORE, 0)
    # RLIMIT_NPROC counts threads across the real UID on the host. Prefer the
    # verified per-container quota when the runtime actually provides one.
    if not verified_cgroup():
        clamp(resource.RLIMIT_NPROC, 48)


def main():
    if os.geteuid() == 0:
        raise SystemExit("Start the isolated Mini-C service as a non-root user.")
    configure_limits()
    from uvicorn import run

    run("execution_service.service:app", uds="/run/minic/minic.sock", access_log=False,
        limit_concurrency=16, proxy_headers=False)


if __name__ == "__main__":
    main()
