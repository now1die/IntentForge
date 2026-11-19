"""Additive Clang transport. Mini-C routes continue to use their existing pipeline."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool

from clang_backend.adapter import MAX_BYTES, MAX_FILES, MAX_UNITS, analyze, capability
from clang_backend.contract import Analysis, Capability

router = APIRouter(tags=["Clang analysis"])
MAX_BODY = 640_000  # includes JSON escapes for the bounded UTF-8 payload


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(default=None, max_length=MAX_BYTES)
    files: dict[str, str] | None = Field(default=None, max_length=MAX_FILES)
    translation_units: list[str] | None = Field(default=None, max_length=MAX_UNITS)
    standard: str = Field(default="c17", max_length=12)

    @model_validator(mode="after")
    def inputs(self):
        if (self.code is None) == (self.files is None):
            raise ValueError("Supply code or files.")
        if (self.code is None) != (self.translation_units is not None):
            raise ValueError("Supply translation_units with files.")
        return self


@router.get("/v1/c-analysis/capability", response_model=Capability)
def c_capability():
    return capability()


@router.post("/v1/c-analysis", response_model=Analysis, openapi_extra={"requestBody": {
    "required": True, "content": {"application/json": {"schema": AnalysisRequest.model_json_schema()}}
}})
async def c_analysis(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            raise HTTPException(status_code=413, detail="The Clang request body exceeds 640 KB.")
        body.extend(chunk)
    try:
        payload = AnalysisRequest.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Invalid Clang request. Supply code or files and translation_units.") from exc
    files = {"main.c": payload.code} if payload.code is not None else payload.files
    entries = ["main.c"] if payload.code is not None else payload.translation_units
    return await run_in_threadpool(analyze, files, entries, payload.standard)
