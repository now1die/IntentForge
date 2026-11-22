"""Endpoint contracts, checked relational repairs and boundary compatibility."""
import json
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase105 import CATEGORIES, ENDPOINT, ROTATION, ZERO
from benchmarks.phase10_fixtures import ROOT as PHASE10
from benchmarks.phase105_fixtures import ROTATION as ROTATION_SOURCE, fixtures
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations


def rows(identifier):
    return next(case for case in fixtures() if case["id"]==identifier)


def analyze(code,vectors,**settings):
    return analyze_intention(code,phase105=True,phase6_entry="f",
                             phase6_examples=tuple(Example(tuple(row["arguments"]),row["expected"]) for row in vectors),
                             **settings)


def verified(case, category):
    result = analyze(case["source"],case["vectors"])
    candidate = next(choice for choice in result.candidates if choice.proposal.category==category)
    suite = tuple((tuple(row["arguments"]),row["expected"]) for row in case["vectors"]+case["holdout_vectors"])
    assert observations(candidate.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    serial = next(c for c in result.to_dict()["candidates"] if c["id"]==candidate.id)
    assert candidate.compiler_valid and serial["requires_approval"]
    assert serial["source_snapshot"]==program_identity(case["source"])
    for edit in serial["edits"]:
        lo,hi = [edit["span"][bound]["offset"] for bound in ("start","end")]
        assert case["source"][lo:hi]==edit["original"]
    return result,candidate


@pytest.mark.parametrize(("name","category"),[
    ("iterative-leftmost-match",ENDPOINT),
    ("duplicate-upper-endpoint",ENDPOINT),
    ("checked-adjacent-score","ADJACENT_CELL_CONSTRAINT"),
    ("coordinated-three-cell-pivot",ROTATION),
    ("division-reserve-sentinel",ZERO),
    ("shifted-digit-aggregate","DERIVED_AGGREGATE_CONSTRAINT"),
])
def test_repair_has_matching_discovery_and_new_inputs(name,category):
    result,candidate = verified(rows(name+"-fault"),category)
    assert result.program_analysis["phase105"]["facts"]
    if name.startswith(("duplicate-upper","coordinated-three")):
        assert len(candidate.proposal.edits)==2


def test_archived_endpoint_repair_and_duplicate_semantics():
    cases = json.loads((PHASE10/"cases-v1.json").read_text())
    case = next(row for row in cases if row["id"]=="duplicate-lower-bound-fault")
    result,choice = verified(case,ENDPOINT)
    assert len(choice.proposal.edits)==2
    assert "saturated_lower" in result.program_analysis["phase105"]["facts"][0]["contracts"]
    ordinary = rows("ordinary-duplicate-match-control")
    assert not [c for c in analyze(ordinary["source"],ordinary["vectors"]).candidates if c.proposal.category in CATEGORIES]


@pytest.mark.parametrize("identifier",[
    "empty-or-singleton-search-control","two-cell-duplicate-pivot-control","lower-insertion-control-control",
    "coordinated-three-cell-pivot-control","signed-noncontiguous-origin-control","division-reserve-sentinel-control",
])
def test_controls_preserve_valid_choices(identifier):
    case = rows(identifier)
    result = analyze(case["source"],case["vectors"])
    assert not any(choice.proposal.category in CATEGORIES for choice in result.candidates)


def test_short_rotation_and_unordered_domain():
    source=ROTATION_SOURCE.replace("cells[3]","cells[2]").replace("cells[2]=c;","").replace("right=2","right=1")
    examples=[{"arguments":[a,b,0],"expected":int(b<a)} for a,b in [(1,4),(5,2),(7,8),(11,-4)]]
    assert analyze(source,examples).program_analysis["phase105"]["status"]=="CONSTRAINTS_ALREADY_AGREE"
    altered=source.replace("cells[middle]>","cells[middle]<")
    assert any(c.proposal.category==ROTATION for c in analyze(altered,examples).candidates)
    examples.append({"arguments":[2,2,0],"expected":0})
    assert not any(c.proposal.category==ROTATION for c in analyze(altered,examples).candidates)
    assert 105 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


def test_changed_signed_inputs_cannot_justify_zero_guard_without_success():
    case = rows("division-reserve-sentinel-fault")
    only_faults = [{"arguments":[x,0],"expected":0} for x in [1,2,3]]
    assert not any(c.proposal.category==ZERO for c in analyze(case["source"],only_faults).candidates)
    assert not any(c.proposal.category==ZERO for c in analyze("int effects=0; "+case["source"],case["vectors"]).candidates)


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"),reason="Requires the restricted Linux worker")
def test_isolated_runtime_guard_and_holdout_preserve_review_policy():
    case = rows("division-reserve-sentinel-fault")
    payload = dict(source=case["source"],entry_point="f",engine_version=105,compare_candidates=True,
                   vectors=case["vectors"])
    with client() as http:
        reply=http.post(URL,json=payload)
        assert reply.status_code==200,reply.text
        data=reply.json()
        assert data["semantic_profile"]==105 and data["program"]==program_identity(case["source"])
        assert data["guided_evidence"]["original"]=="RUNTIME_FAILURE"
        assert data["guided_evidence"]["recommended_candidate"] is None and data["requires_approval"]
        selected=next(c for c in data["candidates"] if data["candidate_categories"][c["id"]]==ZERO)
        held=http.post(URL,json=payload | {"source":selected["source"],"vectors":case["holdout_vectors"],
                                          "compare_candidates":False}).json()
        assert not held["candidates"] and held["original"]["status"]==Status.MATCHES_SUPPLIED_TESTS
        assert http.post(URL,json=payload|{"runtime_observation":{}}).status_code==422
        assert http.post(URL,json=payload|{"language":"c"}).status_code==422
