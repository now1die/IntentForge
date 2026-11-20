"""Loopback-only gateway. Runtime observations come from a private socket."""
import http.client
import json
import os
from pathlib import Path
import socket
import stat
import sys
from threading import BoundedSemaphore

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import ContextLimit, Requirement
from ai.intention_engine import analyze_intention
from ai.intention_requirements import InvalidRequirement
from ai.intention_uncertainty import classify
from execution_service.contracts import (
    Availability, Batch, BatchResult, CandidateReview, Program, RankedProbe, VerifyRequest, VerifyResponse,
)
from .request_body import bounded_body

router = APIRouter(tags=["local behavioral verification"])
LOCAL = {"127.0.0.1", "::1"}
ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000", "http://localhost:8000"}
GATEWAY_SLOTS = BoundedSemaphore(2)
MAX_RESPONSE = 128_000


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=7)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(7)
        self.sock.connect(str(self.path))


def wire(path, endpoint, payload=None):
    connection = UnixHTTP(path)
    try:
        connection.request("POST" if payload is not None else "GET", endpoint, payload,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Private service response is invalid")
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("Private service output is oversized")
        return json.loads(raw)
    finally:
        connection.close()


def gateway(request):
    if os.getenv("INTENTFORGE_VM_GATEWAY") != "isolated-local":
        return Availability(status="disabled", detail="Interactive execution is disabled on this deployment.")
    if sys.platform != "linux":
        return Availability(status="unsupported_environment", detail="Interactive execution requires the verified local Linux service.")
    if (not request.client or request.client.host not in LOCAL or request.url.hostname not in LOCAL | {"localhost"}
            or request.headers.get("origin") not in ORIGINS | {None}
            or any(name in request.headers for name in ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"))):
        return Availability(status="disabled", detail="Interactive execution is limited to the direct local workbench.")
    path = Path(os.getenv("INTENTFORGE_VM_SOCKET", ""))
    if not path.is_absolute():
        return unavailable_socket()
    try:
        socket_stat, parent = path.lstat(), path.parent.lstat()
        if (path != path.resolve() or not stat.S_ISSOCK(socket_stat.st_mode) or not stat.S_ISDIR(parent.st_mode)
                or parent.st_mode & 0o077 or parent.st_uid != os.geteuid() or socket_stat.st_uid != os.geteuid()):
            return unavailable_socket()
    except OSError:
        return unavailable_socket()
    return path


def unavailable_socket():
    return Availability(status="worker_unavailable", detail="The owner-only Mini-C worker socket is unavailable.")


def unhealthy():
    return Availability(status="worker_unhealthy", detail="The local worker did not return verified evidence.")


def get_availability(path):
    try:
        value = Availability.model_validate(wire(path, "/internal/capability"))
        return value if value.status != "available" or value.boundary == "isolated-local-v1" else unhealthy()
    except (ConnectionError, FileNotFoundError):
        return unavailable_socket()
    except (OSError, ValueError, RecursionError, http.client.HTTPException):
        return unhealthy()


def validate_identity(batch, returned):
    if len(returned.runs) != len(batch.programs):
        raise ValueError("Worker returned the wrong number of program runs")
    vectors = tuple(row.model_dump_json() for row in batch.vectors)
    for program, run in zip(batch.programs, returned.runs, strict=True):
        if (run.program != program_identity(program.source) or run.entry_point != batch.entry_point
                or run.candidate_id != program.candidate_id):
            raise ValueError("Worker returned evidence for a different program or test")
        if vectors and (run.execution is None or tuple(row.model_dump_json() for row in run.execution.vectors) != vectors):
            raise ValueError("Worker returned evidence for a different program or test")
        if not vectors and (run.status != Status.ORACLE_UNAVAILABLE or run.execution is not None or run.observations):
            raise ValueError("Worker reported verification without expected values")
    ids = {program.candidate_id for program in batch.programs[1:]}
    for probe in returned.probes:
        observed_ids = {row.candidate_id for row in probe.candidates}
        if (not observed_ids <= ids or len(observed_ids) != len(probe.candidates)
                or isinstance(probe, RankedProbe) != (batch.engine_version == 5)):
            raise ValueError("Worker returned probe evidence for an unexpected candidate")


def verify_local(path, payload):
    identity = {"program": program_identity(payload.source), "entry_point": payload.entry_point}
    if isinstance(path, Availability):
        return VerifyResponse(availability=path, **identity)
    if not GATEWAY_SLOTS.acquire(blocking=False):
        return VerifyResponse(availability=Availability(status="capacity_reached",
                              detail="The local verification gateway is busy."), **identity)
    try:
        return compare(path, payload, identity)
    finally:
        GATEWAY_SLOTS.release()


def compare(path, payload, identity):
    candidates = []
    if payload.compare_candidates:
        requirement = Requirement(function=payload.entry_point, return_expression=payload.return_expression,
                                  condition=payload.condition) if payload.return_expression or payload.condition else None
        try:
            result = analyze_intention(payload.source, requirement, phase35=True, phase5=payload.engine_version == 5,
                                       phase55=payload.engine_version == 55)
            candidates = [(rank, item) for rank, item in enumerate(result.candidates, 1)
                          if item.compiler_valid and len(item.proposed_code) <= 24_000
                          and len(item.proposed_code.encode()) <= 48_000][:4]
        except InvalidRequirement as exc:
            raise HTTPException(status_code=422, detail="The supplied static expression could not be interpreted.") from exc
        except (ContextLimit, RecursionError, TypeError):
            # The isolated original still returns its compiler-admission status.
            pass
    batch = Batch(entry_point=payload.entry_point, vectors=payload.vectors, limits=payload.limits,
                  engine_version=4 if payload.engine_version == 4 else 5,
                  trace=payload.trace, programs=(Program(source=payload.source), *(
                      Program(source=choice.proposed_code, candidate_id=choice.id) for _, choice in candidates
                  )))
    try:
        envelope = wire(path, "/internal/verify", batch.model_dump_json(
            exclude={"engine_version"} if batch.engine_version == 4 else None).encode())
        availability = Availability.model_validate(envelope["availability"])
        if availability.status != "available":
            return VerifyResponse(availability=availability, **identity)
        if availability.boundary != "isolated-local-v1":
            raise ValueError("Private service did not pass its boundary check")
        returned = BatchResult.model_validate(envelope["result"])
        validate_identity(batch, returned)
    except (ConnectionError, FileNotFoundError):
        return VerifyResponse(availability=unavailable_socket(), **identity)
    except (OSError, ValueError, KeyError, TypeError, RecursionError, http.client.HTTPException):
        return VerifyResponse(availability=unhealthy(), **identity)
    original, *alternatives = returned.runs
    reviews = tuple(CandidateReview(id=choice.id, source=choice.proposed_code, static_rank=rank, compiler_valid=True,
                                    static_evidence=classify(choice, ambiguous=False)["tier"],
                                    hypothesis=choice.proposal.assumption, behavior=run)
                    for (rank, choice), run in zip(candidates, alternatives, strict=True))
    passing = tuple(item.id for item in reviews if item.behavior.status == Status.MATCHES_SUPPLIED_TESTS)
    order = review_order(original, reviews, payload.engine_version)
    status = None
    if payload.vectors:
        status = "MULTIPLE_MATCHES" if len(passing) > 1 else "ONE_MATCH" if passing else "NO_OBSERVED_MATCH"
    return VerifyResponse(availability=availability, original=original, candidates=reviews,
                          review_order=order, comparison_status=status, probes=returned.probes, **identity)


def review_order(original, candidates, version):
    issue = original.execution.issue if original.execution else None
    known_failure = original.status == Status.MISMATCHES_SUPPLIED_TESTS or (
        original.status == Status.BEHAVIOR_UNKNOWN and issue and issue.code != "INTERNAL_FAILURE"
    )
    if version in {5, 55} and issue and issue.code in {"STEP_LIMIT", "CALL_DEPTH", "MEMORY_CELLS", "COMPILER_INVALID"}:
        known_failure = True
    if not known_failure:
        return tuple(row.id for row in candidates)
    tiers = {Status.MATCHES_SUPPLIED_TESTS: 0}
    if version in {5, 55}:
        tiers[Status.MISMATCHES_SUPPLIED_TESTS] = 1
    return tuple(row.id for row in sorted(candidates, key=lambda row: tiers.get(row.behavior.status, 2)))


@router.get("/v1/behavioral-verification/capability", response_model=Availability)
async def capability(request: Request):
    path = gateway(request)
    return path if isinstance(path, Availability) else await run_in_threadpool(get_availability, path)


@router.post("/v1/behavioral-verification", response_model=VerifyResponse)
async def verification(request: Request):
    raw = await bounded_body(request, 300_000)
    try:
        payload = VerifyRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid Mini-C source, vectors, entry point or execution limits.") from exc
    return await run_in_threadpool(verify_local, gateway(request), payload)
