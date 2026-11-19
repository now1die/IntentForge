"""Negative-path coverage for the gateway, protocol and disposable supervisor."""
from concurrent.futures import ThreadPoolExecutor
import os
import socket
import sys
from tempfile import TemporaryFile
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routes import behavioral as gateway
from execution_service import service
from execution_service.contracts import Availability, Batch, BatchResult, LocalLimits, Program, TestVector as InputVector
from execution_service.runner import RunnerFailure, collect
from execution_service.worker import run_batch


def local():
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 30001))


PATH = "/v1/behavioral-verification"
BASE = {"source": "int f(int x){return x+1;}", "entry_point": "f",
        "vectors": [{"arguments": [4], "expected": 5}]}


def make_batch():
    return Batch(entry_point="f", vectors=(InputVector(arguments=(4,), expected=5),), limits=LocalLimits(),
                 trace=False, programs=(Program(source=BASE["source"]),))


def test_default_fails_closed_and_static_analysis_passes(monkeypatch):
    monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
    with local() as client:
        assert client.get(PATH + "/capability").json()["status"] == "disabled"
        response = client.post(PATH, json=BASE).json()
        assert response["availability"]["status"] == "disabled" and response["original"] is None
        assert client.post("/analyze", json={"code": BASE["source"]}).json()["success"]


@pytest.mark.parametrize("change", [
    {"language": "c"}, {"entry_point": "x/y"}, {"vectors": []},
    {"vectors": [{"arguments": ["4"], "expected": 5}]}, {"vectors": [{"arguments": [2147483648], "expected": 5}]},
    {"limits": {"steps": 20_001}}, {"limits": {"steps": "20"}}, {"limits": {"memory_cells": True}},
    {"behavioral_evidence": {}}, {"worker_path": "/anything"}, {"command": ["anything"]},
])
def test_malformed_public_fields_rejected(change):
    assert local().post(PATH, json={**BASE, **change}).status_code == 422


def test_compression_and_size_limits():
    assert local().post(PATH, content=b"x" * 300_001).status_code == 413
    assert local().post(PATH, content=b"x", headers={"Content-Encoding": "gzip"}).status_code == 415


def test_gateway_rejects_nonlocal_clients_and_forwarding(monkeypatch):
    monkeypatch.setenv("INTENTFORGE_VM_GATEWAY", "isolated-local")
    assert TestClient(app, base_url="http://127.0.0.1", client=("192.0.2.15", 8000)).get(PATH + "/capability").json()["status"] == "disabled"
    assert local().get(PATH + "/capability", headers={"Forwarded": "for=127.0.0.1"}).json()["status"] == "disabled"
    assert local().get(PATH + "/capability", headers={"Origin": "https://test.invalid"}).json()["status"] == "disabled"


def test_unavailable_or_untrusted_socket(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTFORGE_VM_GATEWAY", "isolated-local")
    control = tmp_path / "vm.sock"
    monkeypatch.setenv("INTENTFORGE_VM_SOCKET", str(control))
    assert local().get(PATH + "/capability").json()["status"] == "worker_unavailable"
    with socket.socket(socket.AF_UNIX) as server:
        server.bind(str(control))
        tmp_path.chmod(0o755)
        assert local().get(PATH + "/capability").json()["status"] == "worker_unavailable"
    tmp_path.chmod(0o700)


def test_private_service_profile_fails_closed(monkeypatch):
    monkeypatch.setattr(service, "deployment_policy", lambda: False)
    assert service.ready().status == "unsupported_environment"


@pytest.mark.parametrize(("program", "expected"), [
    ("import time;time.sleep(2)", "deadline_exceeded"),
    ("raise SystemExit(3)", "worker_unhealthy"),
    ("print('x'*513)", "worker_unhealthy"),
    ("print('[]')", "worker_unhealthy"),
])
def test_supervisor_deadline_crash_and_output_rejection(program, expected):
    with TemporaryFile() as source, pytest.raises(RunnerFailure) as failure:
        collect([sys.executable, "-c", program], source, .12, 512)
    assert failure.value.status == expected


def test_private_worker_capacity_and_recovery(monkeypatch):
    monkeypatch.setattr(service, "ready", lambda: Availability(status="available", detail="fixture",
                                                              boundary="isolated-local-v1"))
    result = run_batch(make_batch()).model_dump(mode="json")
    release, entered = Event(), Event()
    calls = []
    def run(*_):
        calls.append(1)
        if len(calls) == 2:
            entered.set()
        assert release.wait(2)
        return result
    monkeypatch.setattr(service, "run_worker", run)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = (pool.submit(service.verify_batch, make_batch()) for _ in range(2))
        try:
            assert entered.wait(1)
            assert service.verify_batch(make_batch())["availability"].status == "capacity_reached"
        finally:
            release.set()
        assert all(future.result()["result"].runs[0].observations[0].actual == 5 for future in (a, b))
    monkeypatch.setattr(service, "run_worker", lambda *_: {"runs": []})
    assert service.verify_batch(make_batch())["availability"].status == "worker_unhealthy"
    monkeypatch.setattr(service, "run_worker", lambda *_: result)
    assert service.verify_batch(make_batch())["availability"].status == "available"


def test_gateway_validates_worker_identity_before_attaching_evidence(monkeypatch):
    batch = make_batch()
    genuine = run_batch(batch)
    spoofed = genuine.runs[0].model_copy(update={"program": "0" * 64})
    with pytest.raises(ValueError, match="different program"):
        gateway.validate_identity(batch, BatchResult(runs=(spoofed,)))


def test_probe_outcomes_do_not_supply_expected_values_and_preserve_ambiguity():
    batch = Batch(entry_point="f", vectors=(InputVector(arguments=(4, 4), expected=4),), limits=LocalLimits(),
                  trace=False, programs=(
                      Program(source="int f(int a,int b){return lost;}"),
                      Program(source="int f(int a,int b){return a;}", candidate_id="IR-000000000001"),
                      Program(source="int f(int a,int b){return b;}", candidate_id="IR-000000000002"),
                  ))
    result = run_batch(batch)
    assert len(result.probes) <= 8 and any(probe.relation == "disagree" for probe in result.probes)
    assert all(run.status == "MATCHES_SUPPLIED_TESTS" for run in result.runs[1:])
    assert all("expected" not in probe.model_dump_json() for probe in result.probes)


def test_real_isolated_service_when_configured():
    if not os.getenv("INTENTFORGE_VM_SOCKET"):
        pytest.skip("requires the verified local Mini-C container")
    client = local()
    assert client.get(PATH + "/capability").json()["status"] == "available"
    result = client.post(PATH, json={**BASE, "compare_candidates": True, "return_expression": "x*2",
                                     "vectors": [{"arguments": [4], "expected": 8}], "trace": True}).json()
    assert result["availability"]["status"] == "available"
    assert result["original"]["observations"][0]["actual"] == 5
    assert result["candidates"][0]["behavior"]["observations"][0]["actual"] == 8
    assert result["requires_approval"]
    for source, code, limits in (
        ("int f(){for(;;);}", "STEP_LIMIT", {"steps": 40}),
        ("int f(){return f();}", "CALL_DEPTH", {"call_depth": 3}),
        ("int f(){int data[200];return 2;}", "MEMORY_CELLS", {"memory_cells": 10}),
        ("int f(){return 1/0;}", "DIVISION_BY_ZERO", {}),
    ):
        checked = client.post(PATH, json={**BASE, "source": source, "limits": limits,
                                          "vectors": [{"arguments": [], "expected": 0}]}).json()
        assert checked["original"]["execution"]["issue"]["code"] == code
    assert client.post(PATH, json=BASE).json()["original"]["status"] == "MATCHES_SUPPLIED_TESTS"
