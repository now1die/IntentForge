"""Versioned analysis endpoint. The existing correction APIs are independent."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from ai.behavior_oracle import program_identity
from ai.intention_context import ContextLimit, Example, MAX_SOURCE, Requirement
from ai.intention_engine import analyze_intention
from ai.intention_learning import load_expanded_ranker
from ai.intention_ranker import load_ranker
from ai.intention_v3_ranker import load_generalized_ranker
from ai.intention_requirements import InvalidRequirement


router = APIRouter(tags=["intention"])
Scalar = Annotated[StrictInt, Field(ge=-2_147_483_648, le=2_147_483_647)] | StrictBool


class ExampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    args: list[Scalar] = Field(max_length=16)
    expected_return: Scalar


class RequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    function: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z_][A-Za-z_0-9]*$")
    description: str | None = Field(default=None, max_length=400)
    return_expression: str | None = Field(default=None, min_length=1, max_length=160)
    condition: str | None = Field(default=None, min_length=1, max_length=160)
    return_ordinal: int | None = Field(default=None, ge=1, le=3000, strict=True)
    condition_ordinal: int | None = Field(default=None, ge=1, le=3000, strict=True)
    examples: list[ExampleRequest] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def selectors_require_expressions(self):
        if self.return_ordinal is not None and self.return_expression is None and not self.description:
            raise ValueError("A return ordinal needs a return requirement.")
        if self.condition_ordinal is not None and self.condition is None and not self.description:
            raise ValueError("A condition ordinal needs a condition requirement.")
        return self

    def to_domain(self) -> Requirement:
        return Requirement(**self.model_dump(exclude={"examples"}),
                           examples=tuple(Example(tuple(example.args), example.expected_return) for example in self.examples))


class IntentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=MAX_SOURCE)
    requirement: RequirementRequest | None = None
    include_context: bool = False
    engine_version: Literal[2, 3, 4, 5, 55] = 2
    mode: Literal["code_only", "natural_language", "explicit"] | None = None

    @model_validator(mode="after")
    def enforce_mode(self):
        requirement = self.requirement
        if self.engine_version >= 3 and self.mode is None:
            raise ValueError("Choose an analysis mode for engine version 3 or later.")
        if self.mode == "code_only" and requirement is not None:
            raise ValueError("Code-only analysis accepts source alone.")
        if self.mode == "natural_language" and (
            not requirement or not requirement.description or requirement.return_expression is not None or requirement.condition is not None
        ):
            raise ValueError("Natural-language analysis accepts a description without an explicit expression.")
        if self.mode == "explicit" and (
            not requirement or requirement.description is not None or not (requirement.return_expression or requirement.condition)
        ):
            raise ValueError("Explicit analysis needs a return expression or condition without a description.")
        return self


class IntentionResponse(BaseModel):
    finding: str
    decision: str
    ranking: str
    compiler_valid: bool
    behavioral_status: str
    diagnostics: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    notes: list[str]
    attempts: int
    candidates: list[dict[str, Any]]
    context: dict[str, Any] | None
    requirement_status: str | None = None
    recommendation: str | None = None
    structural_scan: dict[str, Any] | None = None
    source_fingerprint: str | None = None


@router.post("/v1/intention-analysis", response_model=IntentionResponse, response_model_exclude_unset=True)
def intention_analysis(request: IntentionRequest) -> dict:
    expanded = None
    if request.engine_version in {5, 55}:
        ranker, status = None, f"V{request.engine_version}_DETERMINISTIC"
    elif request.engine_version >= 3:
        ranker = None
        expanded, status = load_generalized_ranker(request.engine_version)
    elif request.mode is None:
        ranker, status = load_ranker()
    else:
        ranker = None
        expanded, status = load_expanded_ranker()
    requirement = request.requirement.to_domain() if request.requirement else None
    try:
        result = analyze_intention(request.code, requirement, ranker=ranker, ranking_status=status,
                                   enhanced=request.mode is not None, expanded_ranker=expanded,
                                   generalized=request.engine_version >= 3, phase35=request.engine_version == 4,
                                   phase5=request.engine_version == 5, phase55=request.engine_version == 55)
    except InvalidRequirement as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ContextLimit, RecursionError) as exc:
        raise HTTPException(status_code=413, detail="The program exceeds the intention-analysis token or nesting limit.") from exc
    response = result.to_dict(include_context=request.include_context)
    if request.engine_version in {5, 55}:
        response["source_fingerprint"] = program_identity(request.code)
    response.setdefault("requirement_status", None)
    return response
