"""Curated adversarial Mini-C scenarios for ML training and regression."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from compiler.parser import parse
from .error_context import ErrorContext
from .dataset_generator import CorrectionClass

@dataclass(frozen=True)
class ScenarioRecord:
    label: str
    error_context: ErrorContext
    source: str
    expected_fix: str


def _first_context(source: str) -> ErrorContext:
    result = parse(source)
    if result.syntax_errors:
        diagnostic = result.syntax_errors[0]
        return ErrorContext.from_diagnostic(diagnostic, result.tokens, source)
    if result.lexical_errors:
        from .dataset_generator import _lexical_context
        return _lexical_context(result.lexical_errors[0], result.tokens, source)
    raise ValueError(f"scenario has no compiler diagnostic: {source!r}")


def generate_scenario_records(per_class: int = 120) -> list[ScenarioRecord]:
    out: list[ScenarioRecord] = []
    classes = {
        CorrectionClass.DECLARATION_DOT_ERROR.value: [],
        CorrectionClass.DECLARATION_COLON_ERROR.value: [],
        CorrectionClass.SCALAR_ARRAY_USE_ERROR.value: [],
        CorrectionClass.ARRAY_BRACE_INDEX_ERROR.value: [],
    }
    types = ["int", "float", "char", "bool"]
    for i in range(per_class):
        a, b = f"a{i}", f"b{i}"
        typ = types[i % len(types)]
        src = f"{typ} {a}.{b};"
        classes[CorrectionClass.DECLARATION_DOT_ERROR.value].append((src, f"{typ} {a}, {b};"))
        src = f"{typ} {a}:{b};"
        classes[CorrectionClass.DECLARATION_COLON_ERROR.value].append((src, f"{typ} {a}, {b};"))
        n = 1 + (i % 20)
        body = f"int main(){{ {typ} arr{i}; arr{i}" + "{" + f"{n}] = {i+1}; return 0; }}" if i % 2 else f"{typ} arr{i};\narr{i}" + "{" + f"{n}] = {i+1};"
        fixed_body = f"int main(){{ {typ} arr{i}[{n+1}]; arr{i}[{n}] = {i+1}; return 0; }}" if i % 2 else f"{typ} arr{i}[{n+1}];\narr{i}[{n}] = {i+1};"
        classes[CorrectionClass.SCALAR_ARRAY_USE_ERROR.value].append((body, fixed_body))
        body = f"int main(){{ {typ} arr{i}[{n+1}]; arr{i}" + "{" + f"{n}] = {i+1}; return 0; }}" if i % 2 else f"{typ} arr{i}[{n+1}];\narr{i}" + "{" + f"{n}] = {i+1};"
        fixed_body = f"int main(){{ {typ} arr{i}[{n+1}]; arr{i}[{n}] = {i+1}; return 0; }}" if i % 2 else f"{typ} arr{i}[{n+1}];\narr{i}[{n}] = {i+1};"
        classes[CorrectionClass.ARRAY_BRACE_INDEX_ERROR.value].append((body, fixed_body))
    for label, items in classes.items():
        for source, fix in items:
            out.append(ScenarioRecord(label, _first_context(source), source, fix))
    return out
