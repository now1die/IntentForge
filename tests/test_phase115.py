"""Regression evidence for explicit endpoints, cyclic contracts and probes."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase115 import CATEGORIES, CYCLIC, ENDPOINT, RANGE
from benchmarks.phase9_evaluate import rewrites
from benchmarks.phase11_fixtures import fixtures as phase11_cases
from benchmarks.phase115_fixtures import fixtures
from execution_service.contracts import Batch
from execution_service.probes import sample_neighborhood_inputs
from tests.test_phase8 import URL, client, observations
from vm.behavioral_executor import prepare


def case(name,factory=fixtures):
    return next(row for row in factory() if row["id"]==name)


def analyze(row,source=None, examples=None):
    inputs=row["vectors"] if examples is None else examples
    return analyze_intention(source if source is not None else row["source"],phase115=True,phase6_entry="f",
                             phase6_examples=tuple(Example(tuple(row["arguments"]),row["expected"]) for row in inputs))


@pytest.mark.parametrize(("family","category","sites"),[
    ("explicit-upper-argument",ENDPOINT,1),
    ("first-minimum-on-logical-seam",CYCLIC,1),
    ("reaching-maximum-seed",RANGE,2),
])
def test_checked_repairs_preserve_snapshot_and_holdout(family,category,sites):
    row=case(family+"-fault")
    result=analyze(row)
    choice=next(item for item in result.candidates if item.proposal.category==category)
    suite=tuple((tuple(point["arguments"]),point["expected"]) for point in row["vectors"]+row["holdout_vectors"])
    assert choice.compiler_valid and len(choice.proposal.edits)==sites
    assert observations(choice.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    serialized=next(item for item in result.to_dict()["candidates"] if item["id"]==choice.id)
    assert serialized["requires_approval"] and serialized["source_snapshot"]==program_identity(row["source"])
    for edit in serialized["edits"]:
        lo,hi=(edit["span"][side]["offset"] for side in ("start","end"))
        assert edit["original"]==row["source"][lo:hi]


@pytest.mark.parametrize("identifier",["negative-coordinate-control-control","logical-three-cell-control-control",
                                       "first-minimum-on-logical-seam-control","endpoint-zero-control"])
def test_control_contracts_do_not_propose_rewrites(identifier):
    result=analyze(case(identifier))
    assert not any(item.proposal.category in CATEGORIES for item in result.candidates)


def test_explicit_endpoint_recovers_archived_recursive_reset_after_shadow_rewrite():
    row=case("exponential-negative-endpoint-fault",phase11_cases)
    changed=next(source for kind,source,_ in rewrites(row["source"]) if kind=="unused_shadow_scope")
    result=analyze(row,source=changed)
    assert any(item.proposal.category==ENDPOINT for item in result.candidates)
    assert result.program_analysis["phase115"]["facts"][0]["contract"]=="Explicit signed endpoint"


def test_cyclic_does_not_infer_first_if_supplied_coordinate_is_a_later_minimum():
    row=case("first-minimum-on-logical-seam-fault")
    examples=[dict(item) for item in row["vectors"]]
    examples[3]["expected"]=3
    result=analyze(row,examples=examples)
    assert not any(item.proposal.category==CYCLIC for item in result.candidates)


def test_interpolation_disagreement_has_no_expected_output_and_preserves_alternatives():
    row=case("equal-endpoint-probe-fault",phase11_cases)
    result=analyze(row)
    assert result.program_analysis["phase115"]["status"]=="AMBIGUOUS_DISCOVERY"
    alternatives=[item for item in result.candidates if item.proposal.category=="INTERPOLATION_RELATIONAL_CONSTRAINT"]
    assert len(alternatives)==2
    examples=tuple(tuple(row["arguments"]) for row in row["vectors"])
    probes=sample_neighborhood_inputs([prepare(item.proposed_code) for item in alternatives],"f",examples)
    assert probes and len(probes)<=8
    assert all(len(args)==6 and args not in examples for args,basis in probes)
    assert 115 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"),reason="Requires the restricted Linux worker")
def test_isolated_interpolation_evidence_distinguishes_without_recommending():
    row=case("equal-endpoint-probe-fault",phase11_cases)
    payload=dict(source=row["source"],entry_point="f",engine_version=115,vectors=row["vectors"],compare_candidates=True)
    with client() as http:
        reply=http.post(URL,json=payload)
        assert reply.status_code==200,reply.text
        data=reply.json()
        assert data["semantic_profile"]==115 and data["program"]==program_identity(row["source"])
        assert data["guided_evidence"]["original"]=="RUNTIME_FAILURE"
        assert data["guided_evidence"]["recommended_candidate"] is None and data["requires_approval"]
        assert any(pair["status"]=="distinguished" for pair in data["candidate_pairs"]),data["probes"]
        assert max(p["steps"] for p in data["probes"])<200_000
        assert all("expected" not in probe for probe in data["probes"])
        candidate=data["candidates"][0]
        held=http.post(URL,json=payload|{"source":candidate["source"],"vectors":row["holdout_vectors"],
                                       "compare_candidates":False}).json()
        assert held["program"]==program_identity(candidate["source"])
        assert held["original"]["status"]==Status.MATCHES_SUPPLIED_TESTS and not held["candidates"]
        assert http.post(URL,json=payload|{"probe_mode":"sample-neighborhood"}).status_code==422
