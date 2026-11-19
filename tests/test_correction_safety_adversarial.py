"""A compiling edit still needs a trustworthy lexical boundary for automatic use."""

from dataclasses import replace

import pytest

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import assess_repair
from ai.error_predictor import MLCorrectionPredictor
from benchmarks.run import MODEL
from compiler.correction import CandidateValidation, CorrectionAction, CorrectionCandidate, apply_candidate
from compiler.parser import parse
from compiler.source_location import SourceLocation, SourceSpan


def assess(source, needle, insertion, grammar_context, *, action=CorrectionAction.INSERT, width=0, ambiguous=False):
    offset = source.index(needle)
    span = SourceSpan(SourceLocation(1, offset + 1, offset), SourceLocation(1, offset + width + 1, offset + width))
    candidate = CorrectionCandidate(
        id="test", action=action, token_type=None, token_lexeme=None, offset=offset,
        span=span, text=insertion, reason="adversarial fixture", grammar_context=grammar_context, diagnostic_id="test",
    )
    fixed = apply_candidate(source, candidate)
    # The fixture grants target validation to isolate the safety decision.
    valid = parse(fixed).valid
    assert valid, fixed
    validation = CandidateValidation(candidate, fixed, valid, 0, 0, target_resolved=True, relevant_valid=True)
    return assess_repair(candidate, validation, ambiguous=ambiguous)


@pytest.mark.parametrize(
    ("source", "needle", "insert", "context"),
    [
        ("int f(int x){if((x+1>0){return 1;}return 0;}", ">0", ")", "if_condition"),
        ("int f(int x){if(x>0 return 1; return 0;}", " return 1", ")", "if_condition"),
        ("int f(int x){ if(x>0) return 1; return 0; }", " return 1", ";", "if_condition"),
        ("int f(int x){ for(int i=0 i<x;i++){ while(x>0){x--;} } return x; }", " i<x", ";", "for_header"),
        ("int f(int x){ while(x>0){ if(x>1){x--;} return x; }", "\n", "}", "block"),
        ("int a[4]; int f(int i){return a[i+1;}", "+1", "]", "array_access"),
        ("int f(int wet,int dry){return wet dry;}", " dry;", ";", "return_statement"),
    ],
)
def test_structural_candidates_that_can_change_behavior_are_withheld(source, needle, insert, context):
    if needle == "\n":
        source += "\n"
    assert assess(source, needle, insert, context).requires_review


def test_token_replacements_and_multiple_explanations_require_review():
    assert assess("int f(int raw,int row){return row;}", "row;", "raw", "expression",
                  action=CorrectionAction.REPLACE, width=3).requires_review
    assert assess("int f(int a,int b){if(a==b){return 1;}return 0;}", "==", "=", "if_condition",
                  action=CorrectionAction.REPLACE, width=2).requires_review
    assert assess("int f(){return 4}", "}", ";", "return_statement", ambiguous=True).category == "AMBIGUOUS"


def test_policy_keeps_the_simple_workbench_repair():
    source = "int f(int score){if(score>3 {return score;}return 0;}"
    result = CorrectionOrchestrator(MLCorrectionPredictor.load(MODEL)).correct(source)
    assert result.corrections_applied == 1
    assert result.history[0].safety.category == "LOW_RISK_STRUCTURAL"
    assert "score>3)" in result.corrected_source


def test_low_risk_delimiter_must_be_a_real_token_boundary():
    source = "int f(){return 4;} // comment ;"
    offset = source.rindex(";")
    point = SourceLocation(1, offset + 1, offset)
    candidate = CorrectionCandidate("test", CorrectionAction.INSERT, "SEMICOLON", None,
                                    offset, SourceSpan(point, point), ";", "", "return_statement", "")
    validation = CandidateValidation(candidate, source, True, 0, 0, relevant_valid=True)
    assert assess_repair(candidate, validation).category == "UNVERIFIED"
    assert assess_repair(candidate, replace(validation, relevant_valid=False)).category == "UNVERIFIED"
