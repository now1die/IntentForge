"""Interactive correction alternatives and user-selected validation."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ai.correction_options import suggest_correction_options
from compiler.parser import parse
from compiler.semantic_analyzer import analyze_source_semantics

from ..dependencies import get_predictor
from ..schemas import (
    CodeRequest,
    CorrectionOptionsResponse,
    ValidateCorrectionRequest,
    ValidateCorrectionResponse,
)

router = APIRouter(tags=["interactive-correction"])


@router.post("/correction-options", response_model=CorrectionOptionsResponse)
def correction_options(request: CodeRequest, predictor=Depends(get_predictor)) -> CorrectionOptionsResponse:
    result = suggest_correction_options(request.code, predictor)
    return CorrectionOptionsResponse(**result)


@router.post("/validate-correction", response_model=ValidateCorrectionResponse)
def validate_correction(request: ValidateCorrectionRequest) -> ValidateCorrectionResponse:
    parsed = parse(request.corrected_code)
    lexical_errors = len(parsed.lexical_errors)
    syntax_errors = len(parsed.syntax_errors)
    semantic_errors = 0
    if parsed.valid:
        semantic = analyze_source_semantics(request.corrected_code).semantic_result
        semantic_errors = len(semantic.diagnostics) if semantic is not None else 0
    valid = lexical_errors == 0 and syntax_errors == 0
    message = (
        "Correction is compiler-valid and ready to apply."
        if valid
        else f"Correction has {lexical_errors} lexical and {syntax_errors} syntax error(s)."
    )
    if valid and semantic_errors:
        message += f" Semantic analysis reports {semantic_errors} issue(s); review before applying."
    return ValidateCorrectionResponse(
        valid=valid,
        syntax_valid=valid,
        lexical_errors=lexical_errors,
        syntax_errors=syntax_errors,
        semantic_errors=semantic_errors,
        corrected_code=request.corrected_code,
        message=message,
    )
