"""Additive compiler-neutral inspection endpoint."""
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from ai.intention_context import ContextLimit, MAX_SOURCE
from analysis_evidence.contract import EvidenceReport
from analysis_evidence.service import clang, minic
from clang_backend.adapter import analyze
from .clang_analysis import AnalysisRequest, MAX_BODY
from .request_body import bounded_body

router = APIRouter(tags=["compiler evidence"])


class MiniRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["mini-c"]
    code: str = Field(max_length=MAX_SOURCE)


class CRequest(AnalysisRequest):
    language: Literal["c"]


INPUT = TypeAdapter(Annotated[MiniRequest | CRequest, Field(discriminator="language")])


@router.post("/v1/compiler-evidence", response_model=EvidenceReport, openapi_extra={"requestBody": {
    "required": True, "content": {"application/json": {"schema": {"oneOf": [MiniRequest.model_json_schema(), CRequest.model_json_schema()]}}}
}})
async def compiler_evidence(request: Request):
    try:
        payload = INPUT.validate_json(await bounded_body(request, MAX_BODY))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid compiler evidence request.") from exc
    if isinstance(payload, MiniRequest):
        try:
            return await run_in_threadpool(minic, payload.code)
        except (ContextLimit, RecursionError, UnicodeError) as exc:
            raise HTTPException(status_code=413, detail="The Mini-C evidence request exceeds its source limits.") from exc
    files = {"main.c": payload.code} if payload.code is not None else payload.files
    entries = ["main.c"] if payload.code is not None else payload.translation_units
    return clang(await run_in_threadpool(analyze, files, entries, payload.standard))
