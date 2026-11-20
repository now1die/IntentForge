"""Phase 5 probe accounting, legacy protocol and restricted service integration."""

import os
import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import Status
from backend.app.main import app
from backend.app.routes.behavioral import validate_identity
from execution_service.contracts import Batch, LocalLimits, Program
from execution_service.probes import compare_probes, ranked_probes
from execution_service.worker import run_batch
from vm.interpreter import prepare
from vm.runtime import WorkBudget

URL = "/v1/behavioral-verification"
SOURCE = "int f(int left,int right){return missing;}"
LEFT = "int f(int left,int right){return left;}"
RIGHT = "int f(int left,int right){return right;}"


def prepared(*sources):
    return [(f"IR-{i:012x}", prepare(source)) for i, source in enumerate(sources)]


def test_ranked_boundary_probes_cover_pairs_and_identify_candidate_specific_failure():
    sources = prepared("int f(int x){return x;}", "int f(int x){if(15==x){return x+1;}return x;}",
                       "int f(int x){if(x==15){return x/(x-x);}return x;}")
    legacy = compare_probes(sources, "f", (), LocalLimits(), WorkBudget(1000))
    budget = WorkBudget(1000)
    current = ranked_probes(sources, "f", (), LocalLimits(), budget)
    first = current[0]
    assert (first.arguments, first.separated_pairs, first.new_pairs) == ((15,), 3, 3)
    assert first.assessment == "different_values" and first.input_basis == "boundary"
    assert {item.status for item in first.candidates} == {"observed", "runtime_failure"}
    assert all(row.relation == "agree" for row in legacy)
    assert len(current) <= 8 and sum(row.steps for row in current) == 1000 - budget.remaining
    assert all("expected" not in row.model_dump_json() for row in current)


def test_candidate_limits_distinct_from_aggregate_exhaustion_and_local_array_edges():
    sources = prepared("int f(int x){return x;}", "int f(int x){if(x==9){for(;;);}return x;}")
    probes = ranked_probes(sources, "f", (), LocalLimits(steps=40), WorkBudget(1000))
    assert probes[0].arguments == (9,) and probes[0].assessment == "candidate_execution_limit"
    exhausted = ranked_probes(sources, "f", (), LocalLimits(), WorkBudget(5))
    assert sum(row.steps for row in exhausted) <= 5
    assert not any(row.separated_pairs for row in exhausted)
    arrays = prepared("int f(int x){return x;}", "int f(int x){int a[7];a[x]=x;return a[x];}")
    edge = ranked_probes(arrays, "f", (), LocalLimits(), WorkBudget(1000))[0]
    assert edge.arguments == (7,) and edge.assessment == "candidate_runtime_failure"


def test_no_expected_vectors_can_produce_a_match():
    batch = Batch(engine_version=5, entry_point="f", vectors=(), trace=False, limits=LocalLimits(),
                  programs=(Program(source=SOURCE), Program(source=LEFT, candidate_id="IR-000000000001"),
                            Program(source=RIGHT, candidate_id="IR-000000000002")))
    reply = run_batch(batch)
    validate_identity(batch, reply)
    assert all(row.status == Status.ORACLE_UNAVAILABLE for row in reply.runs)
    assert reply.probes and reply.probes[0].separated_pairs == 1
    spoofed = reply.runs[0].model_copy(update={"status": Status.BEHAVIOR_UNKNOWN})
    with pytest.raises(ValueError, match="without expected values"):
        validate_identity(batch, reply.model_copy(update={"runs": (spoofed, *reply.runs[1:])}))


def test_observation_only_requires_explicit_version_and_rejects_client_evidence(monkeypatch):
    monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
    client = TestClient(app)
    msg = {"source": SOURCE, "vectors": [], "entry_point": "f", "compare_candidates": True}
    assert client.post(URL, json=msg).status_code == 422
    assert client.post(URL, json={**msg, "engine_version": 5}).json()["availability"]["status"] == "disabled"
    assert client.post(URL, json={**msg, "engine_version": 5, "comparison_status": "ONE_MATCH"}).status_code == 422


def test_live_ambiguity_requires_expected_outputs_to_change_review_order():
    if not os.getenv("INTENTFORGE_VM_SOCKET"):
        pytest.skip("Requires the restricted Mini-C service")
    client = TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 35000))
    msg = {"source": SOURCE, "entry_point": "f", "engine_version": 5, "compare_candidates": True}
    observed = client.post(URL, json={**msg, "vectors": []}).json()
    assert observed["availability"]["status"] == "available"
    ids = [row["id"] for row in observed["candidates"]]
    assert len(ids) == 2 and observed["review_order"] == ids and observed["comparison_status"] is None
    equal = {"arguments": [4, 4], "expected": 4}
    ambiguous = client.post(URL, json={**msg, "vectors": [equal]}).json()
    assert ambiguous["comparison_status"] == "MULTIPLE_MATCHES"
    alternative = next(row for row in ambiguous["candidates"] if row["id"] == ids[1])
    expected = 8 if "return left;" in alternative["source"] else 3
    vectors = [equal, {"arguments": [8, 3], "expected": expected}]
    distinguished = client.post(URL, json={**msg, "vectors": vectors}).json()
    assert distinguished["comparison_status"] == "ONE_MATCH" and distinguished["review_order"][0] == ids[1]
    assert distinguished["candidates"][0]["static_rank"] == 1 and distinguished["requires_approval"]
