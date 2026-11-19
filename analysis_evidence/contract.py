"""Language-neutral evidence. Offsets use UTF-8 bytes and UTF-16 editor units."""
from typing import Literal

from pydantic import BaseModel, Field


class Position(BaseModel):
    line: int
    column: int
    byte_offset: int


class Span(BaseModel):
    file: str
    start: Position
    end: Position
    origin: Literal["physical", "expansion", "spelling"] = "physical"


class Diagnostic(BaseModel):
    severity: Literal["note", "warning", "error", "fatal"]
    message: str
    category: str | None = None
    code: str | None = None
    phase: Literal["lexical", "syntax", "semantic", "preprocessing", "unclassified"]
    span: Span | None = None
    related: list[Span] = Field(default_factory=list)
    notes: list["Diagnostic"] = Field(default_factory=list)


class Node(BaseModel):
    id: int
    parent: int | None
    kind: str
    name: str | None = None
    span: Span | None = None
    spelling_span: Span | None = None
    scope: int | None = None
    declaration: bool = False
    reference: int | None = None
    type: str | None = None
    canonical_type: str | None = None
    parameter_types: list[str] | None = None
    result_type: str | None = None
    variadic: bool | None = None


class TranslationUnit(BaseModel):
    entry: str
    ast: Literal["available", "partial", "unavailable"]
    diagnostics: list[Diagnostic]
    nodes: list[Node]


class Capability(BaseModel):
    status: Literal["available", "unavailable"]
    detail: str
    version: str | None = None
    standards: list[str] = Field(default_factory=lambda: ["c99", "c11", "c17", "c23"])
    features: list[str] = Field(default_factory=lambda: ["diagnostics", "ast", "declarations", "types", "multiple_translation_units"])
    unsupported: list[str] = Field(default_factory=lambda: ["intelligent_repair", "execution", "linking", "build_systems"])


class Analysis(BaseModel):
    provider: Literal["clang"] = "clang"
    status: Literal["ok", "syntax_errors", "semantic_errors", "compiler_errors",
                    "unavailable", "unsupported_configuration", "request_limit", "timeout"]
    detail: str | None = None
    version: str | None = None
    standard: str
    files: list[str] = Field(default_factory=list)
    units: list[TranslationUnit] = Field(default_factory=list)


class ScopeEvidence(BaseModel):
    id: int
    kind: str
    parent: int | None = None
    span: Span | None = None


class EvidenceUnit(TranslationUnit):
    scopes: list[ScopeEvidence] = Field(default_factory=list)
    control_flow_nodes: list[int] = Field(default_factory=list)


class EvidenceReport(BaseModel):
    schema_version: Literal[1] = 1
    language: Literal["mini-c", "c"]
    provider: Literal["ply-mini-c", "clang"]
    version: str | None = None
    status: str
    detail: str | None = None
    files: list[str]
    units: list[EvidenceUnit]
    unsupported: list[str]
