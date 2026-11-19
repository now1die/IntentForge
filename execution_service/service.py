"""Private Unix-socket service. All submitted Mini-C runs in a child."""
import os
import resource
from pathlib import Path
import sys
from threading import BoundedSemaphore
from time import monotonic

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from backend.app.routes.request_body import bounded_body

from .contracts import Availability, Batch, BatchResult
from .launch import verified_cgroup
from .runner import RunnerFailure, run_worker

app = FastAPI(title="Private IntentForge Mini-C worker", docs_url=None, redoc_url=None, openapi_url=None)
SLOTS = BoundedSemaphore(2)
PROBE_SLOT = BoundedSemaphore(1)
VERIFIED_UNTIL = 0.0
BOUNDARY = "isolated-local-v1"


def deployment_policy() -> bool:
    """Check local profile requirements independently of the startup command."""
    if sys.platform != "linux" or os.geteuid() == 0:
        return False
    try:
        status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
        if (int(status["CapEff"].strip(), 16) or status["NoNewPrivs"].strip() != "1"
                or status["Seccomp"].strip() != "2"):
            return False
        if not os.statvfs("/").f_flag & os.ST_RDONLY:
            return False
        interfaces = {line.split(":", 1)[0].strip() for line in Path("/proc/net/dev").read_text().splitlines()[2:]}
        if interfaces != {"lo"}:
            return False
        return verified_quotas()
    except (OSError, ValueError, KeyError):
        return False


def verified_quotas():
    if verified_cgroup():
        return True
    # Rootless daemons may present the parent cgroup. The service requires
    # real kernel process limits in that case. Each disposable child further
    # restricts its address space and CPU and disallows process creation.
    memory = resource.getrlimit(resource.RLIMIT_AS)[1]
    processes = resource.getrlimit(resource.RLIMIT_NPROC)[1]
    return 0 < memory <= 384 * 1024**2 and 0 < processes <= 48


def ready():
    global VERIFIED_UNTIL
    if not deployment_policy():
        return Availability(status="unsupported_environment", detail="The private Linux service isolation profile was not verified.")
    if monotonic() >= VERIFIED_UNTIL:
        if not PROBE_SLOT.acquire(blocking=False):
            return Availability(status="capacity_reached", detail="The isolated service is checking its worker.")
        try:
            if run_worker("probe").get("boundary") != BOUNDARY:
                raise RunnerFailure("worker_unhealthy")
            VERIFIED_UNTIL = monotonic() + 10
        except RunnerFailure as failure:
            return Availability(status=failure.status, detail="The isolated worker startup check failed.")
        finally:
            PROBE_SLOT.release()
    return Availability(status="available", detail="Verified restricted Mini-C service for this local deployment.", boundary=BOUNDARY)


@app.get("/internal/capability", response_model=Availability)
def capability():
    return ready()


def verify_batch(batch):
    global VERIFIED_UNTIL
    availability = ready()
    if availability.status != "available":
        return {"availability": availability, "result": None}
    if not SLOTS.acquire(blocking=False):
        return {"availability": Availability(status="capacity_reached", detail="Both isolated worker slots are in use."), "result": None}
    try:
        result = BatchResult.model_validate(run_worker("verify", batch.model_dump_json().encode()))
        return {"availability": availability, "result": result}
    except (RunnerFailure, ValidationError) as exc:
        VERIFIED_UNTIL = 0.0
        status = exc.status if isinstance(exc, RunnerFailure) else "worker_unhealthy"
        return {"availability": Availability(status=status, detail="The isolated worker returned no verified result."), "result": None}
    finally:
        SLOTS.release()


@app.post("/internal/verify")
async def verify(request: Request):
    raw = await bounded_body(request, 384_000)
    try:
        batch = Batch.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid private Mini-C verification request.") from exc
    return await run_in_threadpool(verify_batch, batch)
