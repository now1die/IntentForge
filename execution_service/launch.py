"""Private service entry point. Install actual self-limits before serving."""
import os
import resource


def clamp(resource_id, maximum):
    soft, hard = resource.getrlimit(resource_id)
    ceiling = min(hard, maximum) if hard != resource.RLIM_INFINITY else maximum
    target = min(soft, ceiling) if soft != resource.RLIM_INFINITY else ceiling
    resource.setrlimit(resource_id, (target, ceiling))


def main():
    if os.geteuid() == 0:
        raise SystemExit("Start the isolated Mini-C service as a non-root user.")
    clamp(resource.RLIMIT_AS, 384 * 1024**2)
    clamp(resource.RLIMIT_NPROC, 48)
    clamp(resource.RLIMIT_CORE, 0)
    from uvicorn import run

    run("execution_service.service:app", uds="/run/minic/minic.sock", access_log=False, limit_concurrency=16)


if __name__ == "__main__":
    main()
