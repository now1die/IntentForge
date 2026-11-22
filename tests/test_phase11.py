"""Relational repairs, preserved policy and guarded compiler observations."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase11 import CYCLIC, HELPER, INTERPOLATION, RANGE
from benchmarks.phase9_evaluate import rewrites
from benchmarks.phase105_fixtures import fixtures as archived
from benchmarks.phase11_fixtures import fixtures
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations


def case(name, source=fixtures):
    return next(row for row in source() if row["id"]==name)


def analyze(row, *, source=None, profile="phase11", examples=None):
    return analyze_intention(row["source"] if source is None else source, phase6_entry="f",
                             phase6_examples=tuple(Example(tuple(item["arguments"]),item["expected"])
                                                   for item in (row["vectors"] if examples is None else examples)),
                             **{profile:True})


def verified(row,category,count):
    result=analyze(row)
    candidates=[choice for choice in result.candidates if choice.proposal.category==category
                and len(choice.proposal.edits)==count]
    assert candidates
    choice=candidates[0]
    suite=tuple((tuple(item["arguments"]),item["expected"]) for item in row["vectors"]+row["holdout_vectors"])
    assert choice.compiler_valid
    assert observations(choice.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    detail=next(item for item in result.to_dict()["candidates"] if item["id"]==choice.id)
    assert detail["source_snapshot"]==program_identity(row["source"]) and detail["requires_approval"]
    for edit in detail["edits"]:
        lower,upper=(edit["span"][key]["offset"] for key in ("start","end"))
        assert row["source"][lower:upper]==edit["original"]
    return result


@pytest.mark.parametrize(("name","category","sites"),[
    ("equal-endpoint-probe",INTERPOLATION,2),
    ("duplicate-cyclic-pivot",CYCLIC,1),
    ("linked-aggregate-origin",RANGE,2),
    ("signed-unity-boundary",HELPER,1),
])
def test_relational_categories_and_independent_inputs(name,category,sites):
    result=verified(case(name+"-fault"),category,sites)
    report=result.program_analysis["phase11"]
    assert report["facts"] and report["trials"]<=24
    assert all(fact["scope"]=="SUPPLIED_EXAMPLES_ONLY" for fact in report["facts"])
    assert any(fact["lexical_bindings"] for fact in report["facts"])


@pytest.mark.parametrize("name",["iterative-leftmost-match-fault","duplicate-upper-endpoint-fault"])
def test_shadow_scopes_preserve_binding_equivalent_endpoint_repairs(name):
    row=case(name,archived)
    transformed=next(source for kind,source,_ in rewrites(row["source"]) if kind=="unused_shadow_scope")
    before=analyze(row,source=transformed,profile="phase105")
    assert all(c.proposal.category!="ENDPOINT_SEARCH_CONSTRAINT" for c in before.candidates)
    after=analyze(row,source=transformed)
    choice=next(c for c in after.candidates if c.proposal.category=="ENDPOINT_SEARCH_CONSTRAINT")
    suite=tuple((tuple(test["arguments"]),test["expected"]) for test in row["vectors"]+row["holdout_vectors"])
    assert observations(choice.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    assert "phaseprobe" in choice.proposed_code


def test_interpolation_preserves_missing_key_and_checked_overflow():
    row=case("equal-endpoint-probe-fault")
    incompatible=[*row["vectors"],{"arguments":[0,-2_000_000_000,-1_000_000_000,0,1,2],"expected":2}]
    result=analyze(row,examples=incompatible)
    assert not any(c.proposal.category==INTERPOLATION and len(c.proposal.edits)==2 for c in result.candidates)
    agree=analyze(case("equal-endpoint-probe-control"))
    assert agree.program_analysis["phase11"]["status"]=="CONSTRAINTS_ALREADY_AGREE"


def test_cyclic_model_abstains_on_nonrotation_and_correct_logical_prefixes():
    row=case("duplicate-cyclic-pivot-fault")
    incoherent=[*row["vectors"],{"arguments":[9,3,12,0,2,5],"expected":3}]
    assert not any(c.proposal.category==CYCLIC for c in analyze(row,examples=incoherent).candidates)
    assert analyze(case("logical-cyclic-singleton-control")).program_analysis["phase11"]["status"]=="CONSTRAINTS_ALREADY_AGREE"


def test_zero_contract_requires_two_operand_directions():
    row=case("signed-unity-boundary-fault")
    inputs=[item for item in row["vectors"] if item["arguments"][0]!=0]
    assert not any(c.proposal.category==HELPER for c in analyze(row,examples=inputs).candidates)
    assert 11 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"),reason="Requires the restricted Linux worker")
def test_interpolation_runtime_and_fresh_holdout_keep_approval_bound_to_source():
    row=case("equal-endpoint-probe-fault")
    payload=dict(source=row["source"],entry_point="f",engine_version=11,vectors=row["vectors"],compare_candidates=True)
    with client() as http:
        reply=http.post(URL,json=payload)
        assert reply.status_code==200,reply.text
        data=reply.json()
        assert data["semantic_profile"]==11 and data["program"]==program_identity(row["source"])
        assert data["guided_evidence"]["original"]=="RUNTIME_FAILURE"
        assert data["guided_evidence"]["recommended_candidate"] is None and data["requires_approval"]
        choice=next(c for c in data["candidates"] if len(data["candidate_details"][c["id"]]["edits"])==2)
        held=http.post(URL,json=payload|{"source":choice["source"],"vectors":row["holdout_vectors"],
                                       "compare_candidates":False}).json()
        assert held["program"]==program_identity(choice["source"])
        assert held["original"]["status"]==Status.MATCHES_SUPPLIED_TESTS and not held["candidates"]
        assert http.post(URL,json=payload|{"runtime_observation":{}}).status_code==422
        assert http.post(URL,json=payload|{"language":"c"}).status_code==422
