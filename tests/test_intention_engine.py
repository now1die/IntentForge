"""Tests for contextual facts, bounded proposals and abstention."""

import json

import pytest

from ai.correction_safety import repair_key
from ai.intention_context import ContextLimit, Example, Requirement, build_context
from ai.intention_engine import analyze_intention
from ai.intention_ranker import MODEL_PATH, load_ranker
from ai.intention_requirements import InvalidRequirement
from benchmarks.phase2_audit import audit
from benchmarks.phase2_data import DEVELOPMENT, FINAL, generate


def keys(result):
    return [repair_key(item.proposed_code) for item in result.candidates]


def test_nested_scope_resolves_shadowed_identifier_using_compiler_symbols():
    context = build_context("int demo(int x){ int answer=x; { int answer=2; x=answer; } return answer; }")
    data = context.to_dict()
    bindings = [node for node in data["nodes"] if node["kind"] == "Identifier" and node["name"] == "answer"]
    assert len(bindings) == 2 and bindings[0]["binding"] != bindings[1]["binding"]
    assert all(node["parent"] is not None and node["function"] == "demo" for node in bindings)
    assert all(node["type"] == "int" for node in bindings)
    assert context.to_dict() == build_context(context.source).to_dict()


def test_multiple_functions_expose_signatures_and_enclosing_function():
    context = build_context("int low(int n){return n;} int outer(){while(true){return low(2);} return 0;}")
    payload = context.to_dict()
    assert any(symbol["type"]["display"] == "function(int) -> int" for symbol in payload["symbols"])
    assert any(node["kind"] == "WhileStatement" and node["function"] == "outer" for node in payload["nodes"])
    assert any(node["kind"] == "FunctionCall" and node["type"] == "int" for node in payload["nodes"])


@pytest.mark.parametrize("source", ["int outer(){ int inner(){ return 0; } return 1;}", "int f(int n){return (n+;"])
def test_invalid_and_nested_function_syntax_does_not_invent_an_ast(source):
    context = build_context(source).to_dict()
    assert context["nodes"] == [] and context["symbols"] == []
    assert context["ast_status"] == "MISSING_INCOMPLETE_SYNTAX"
    assert context["tokens"] and context["diagnostics"]


@pytest.mark.parametrize(
    ("source", "requirement", "accepted"),
    [
        ("int add(int a,int b){return a-b;}", Requirement(description="Return the sum of a and b."),
         "int add(int a,int b){return a+b;}"),
        ("int f(int age){if(age<18){return 1;}return 0;}", Requirement(condition="age>=18"),
         "int f(int age){if(age>=18){return 1;}return 0;}"),
        ("int f(int x){int result=x*x;return x;}", Requirement(return_expression="result"),
         "int f(int x){int result=x*x;return result;}"),
        ("int f(){return;}", Requirement(return_expression="13"), "int f(){return 13;}"),
        ("int f(int n){if(n>7){return n+1;}return 0;}",
         Requirement(condition="n>=7", return_expression="n-1", return_ordinal=1),
         "int f(int n){if(n>=7){return n-1;}return 0;}"),
        ("int g(int a,int b){return a-b;} int f(int x){return g(3,x);}",
         Requirement(function="f", return_expression="g(x,3)"),
         "int g(int a,int b){return a-b;} int f(int x){return g(x,3);}"),
        ("int a[6]; int f(int i){return a[i+1];}", Requirement(return_expression="a[i-1]"),
         "int a[6]; int f(int i){return a[i-1];}"),
    ],
)
def test_specification_repairs_are_revalidated_and_require_approval(source, requirement, accepted):
    result = analyze_intention(source, requirement)
    assert keys(result)[0] == repair_key(accepted)
    assert result.decision == "STRONG_SPECIFICATION_EVIDENCE"
    top = result.to_dict()["candidates"][0]
    assert top["compiler_valid"] and top["safety"]["requires_review"]
    assert top["behavioral_status"] == "ORACLE_UNAVAILABLE"
    assert any(item["kind"] == "USER_REQUIREMENT" for item in top["evidence"])
    assert len(set(keys(result))) == len(keys(result))


@pytest.mark.parametrize(
    ("source", "accepted"),
    [
        ("int f(int raw){int row=7;return ra;}", "int f(int raw){int row=7;return raw;}"),
        ("int g(int x){return x;} int f(int p){return g(p,1);}", "int g(int x){return x;} int f(int p){return g(p);}"),
        ("char f(int code,char value){char answer=code;return answer;}", "char f(int code,char value){char answer=value;return answer;}"),
        ("int v[4]; int f(int n){return v(n);}", "int v[4]; int f(int n){return v[n];}"),
        ("int f(int raw,int add){int result=rw;return ad;}", "int f(int raw,int add){int result=raw;return add;}"),
    ],
)
def test_semantic_candidates_use_symbols_types_and_local_edits(source, accepted):
    result = analyze_intention(source)
    assert result.finding == "COMPILER_ERROR"
    assert repair_key(accepted) in keys(result)
    assert all(item["safety"]["requires_review"] for item in result.to_dict()["candidates"])


def test_description_interpretation_requires_corresponding_ast_evidence():
    source = "int total(int price,int quantity){int result=price*quantity;return price;}"
    result = analyze_intention(source, Requirement(description="Return the total cost."))
    assert result.candidates[0].proposed_code.endswith("return result;}")
    assert "supported reading" in result.candidates[0].proposal.evidence[1].detail
    no_product = analyze_intention("int total(int price,int quantity){return price;}",
                                   Requirement(description="Return the total cost."))
    assert no_product.decision == "INSUFFICIENT_CONTEXT" and not no_product.candidates
    eligible = analyze_intention("int eligible(int age){if(age<18)return 1;return 0;}",
                                 Requirement(description="Eligibility begins at 18."))
    assert eligible.candidates and "age >= 18" in eligible.candidates[0].proposed_code
    no_positive_branch = analyze_intention("int eligible(int age){if(age<18)return 0;return 1;}",
                                         Requirement(description="Eligibility begins at 18."))
    assert not no_positive_branch.candidates


def test_names_do_not_create_intent_and_weak_heuristic_abstains():
    assert not analyze_intention("int square(int x){return x+x;}").candidates
    result = analyze_intention("int billed(int price,int unit){int cost=price*unit;return price;}")
    assert result.finding == "HEURISTIC_SUSPICION" and result.decision == "INSUFFICIENT_CONTEXT"
    assert not result.candidates


def test_ambiguity_and_examples_alone_are_not_treated_as_proof():
    result = analyze_intention("int f(int pin,int pen){return pnn;}")
    assert result.decision == "AMBIGUOUS" and len(result.candidates) == 2
    examples = Requirement(examples=(Example((5,), 10),))
    result = analyze_intention("int f(int x){return x-2;}", examples)
    assert result.decision == "INSUFFICIENT_CONTEXT" and not result.candidates
    result = analyze_intention("int f(int x){if(x>0){return x;}return 0;}", Requirement(return_expression="x+1"))
    assert result.decision == "INSUFFICIENT_CONTEXT" and not result.candidates


@pytest.mark.parametrize("invalid", ["x; return 0", "x=1", "x++", "x +", "  "])
def test_invalid_requirement_expression_rejected(invalid):
    with pytest.raises(InvalidRequirement):
        analyze_intention("int f(int x){return x;}", Requirement(return_expression=invalid))


def test_a_specification_matching_ast_cannot_force_a_non_compiling_proposal():
    result = analyze_intention("int f(int x){return x;}", Requirement(return_expression="missing"))
    assert result.finding == "SPECIFICATION_SUPPORTED_SUSPICION" and not result.candidates
    result = analyze_intention("int f(int x){return (x+1);}", Requirement(return_expression="x + 1"))
    assert result.decision == "REQUIREMENT_SHAPE_MATCHES" and not result.candidates


def test_ranking_reproduces_and_learned_model_is_bounded_to_supported_role(tmp_path):
    ranker, status = load_ranker(MODEL_PATH)
    assert ranker and status == "LEARNED"
    source = "int f(int raw){int fallback=1;int result=raw;result+=3;return fallbac;}"
    first = analyze_intention(source, ranker=ranker, ranking_status=status)
    second = analyze_intention(source, ranker=ranker, ranking_status=status)
    assert first.to_dict() == second.to_dict()
    assert first.ranking == "LEARNED" and first.candidates[0].relative_score is not None
    assignment = "int f(int raw){int fallback=1;int result=raw;result+=3;result=fallbac;return result;}"
    outside_scope = analyze_intention(assignment, ranker=ranker, ranking_status=status)
    assert len(outside_scope.candidates) > 1 and outside_scope.ranking == "DETERMINISTIC_OUTSIDE_MODEL_SCOPE"
    assert all(item.relative_score is None for item in outside_scope.candidates)
    absent, fallback = load_ranker(tmp_path / "missing.joblib")
    assert absent is None and fallback == "ARTIFACT_UNAVAILABLE"
    result = analyze_intention(source, ranker=absent, ranking_status=fallback)
    assert result.ranking == fallback and result.candidates
    assert all(item.relative_score is None for item in result.candidates)


def test_resource_limits_and_cooperative_timeout():
    source = "int f(int left,int right){return lef;}"
    result = analyze_intention(source, budget_seconds=0)
    assert result.decision == "BUDGET_EXHAUSTED" and result.attempts == 0
    filtered = analyze_intention(source, candidate_budget=1)
    assert filtered.attempts <= 1 and len(filtered.candidates) <= 1
    with pytest.raises(ContextLimit):
        build_context("int f(){return " + "("*70 + "1" + ")"*70 + ";}")


def test_phase2_training_provenance_and_cross_split_leak_detection():
    development = json.loads(DEVELOPMENT.read_text())
    assert development == generate()
    final = json.loads(FINAL.read_text())["cases"]
    assert audit(development["cases"], final)["issues"] == []
    probe = {**development["cases"][0], "id": "cross", "split": "final"}
    errors = audit(development["cases"][:1], [probe], historical=[], archives=[])["issues"]
    assert any("crosses splits" in item for item in errors)
    assert any("template" in item for item in errors)
