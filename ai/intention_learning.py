"""Trusted category-gated Phase 2.5 ranking artifacts and AST features."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from math import isfinite
from pathlib import Path
from time import monotonic
import re

import joblib
from sklearn.pipeline import Pipeline

from compiler.ast_nodes import ArrayAccess, Assignment, FunctionCall, Identifier, UpdateExpression
from compiler.symbol_table import ScopeKind

from .intention_context import enclosing


FEATURE_VERSION = 1
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "intention_ranker_v2.joblib"


@dataclass(frozen=True)
class ExpandedRanker:
    models: dict[str, Pipeline]
    selected: dict[str, str]

    def order(self, group, *, experimental=None, deadline=None):
        # Preserve strata and cross-category slots. Only comparable alternatives
        # in the same learned category receive a numerical margin.
        slots = {}
        for index, candidate in enumerate(group):
            # Current labels cover compiler-diagnosed repairs. A purely
            # heuristic edit uses deterministic ordering pending its own study.
            if any(fact.kind == "COMPILER_DIAGNOSTIC" for fact in candidate.proposal.evidence):
                slots.setdefault(candidate.proposal.category, []).append(index)
        ordered = list(group)
        for category, indices in slots.items():
            method = experimental or self.selected.get(category)
            if len(indices) < 2 or method not in self.models:
                continue
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Ranker budget expired")
            model = self.models[method]
            cases = [group[index] for index in indices]
            rows = [item.features for item in cases]
            if method == "pairwise":
                pairs = [(i, j, difference(a, b)) for i, a in enumerate(rows) for j, b in enumerate(rows) if i != j]
                margins = [0.0] * len(rows)
                for (i, _, _), value in zip(pairs, model.decision_function([pair[2] for pair in pairs]), strict=True):
                    margins[i] += float(value)
                scores = [value / (len(rows) - 1) for value in margins]
            else:
                scores = model.decision_function(rows)
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Ranker budget expired")
            for candidate, score in zip(cases, scores, strict=True):
                if not isfinite(score):
                    raise ValueError("Non-finite model rank margin")
                candidate.relative_score = float(score)
            for slot, candidate in zip(indices, sorted(cases, key=lambda item: -item.relative_score), strict=True):
                ordered[slot] = candidate
        return ordered


def difference(left, right):
    """Signed numerical and one-hot differences for the pairwise experiment."""
    def encode(row):
        return {f"{key}={value}" if isinstance(value, str) else key: 1 if isinstance(value, str) else value
                for key, value in row.items()}
    a, b = encode(left), encode(right)
    return {key: a.get(key, 0) - b.get(key, 0) for key in sorted(a.keys() | b.keys())}


@lru_cache(maxsize=1)
def load_expanded_ranker(path=MODEL_PATH):
    try:
        if Path(path).stat().st_size > 2_000_000:
            return None, "EXPANDED_ARTIFACT_INCOMPATIBLE"
        artifact = joblib.load(path)
        if artifact["feature_version"] != FEATURE_VERSION:
            return None, "EXPANDED_ARTIFACT_INCOMPATIBLE"
        models = artifact["models"]
        selected = artifact["selected"]
        if (not isinstance(selected, dict) or not all(isinstance(model, Pipeline) for model in models.values())
                or not all(name in models for name in selected.values())):
            return None, "EXPANDED_ARTIFACT_INCOMPATIBLE"
        return ExpandedRanker(models, selected), "EXPANDED_LEARNED"
    except Exception:
        return None, "EXPANDED_ARTIFACT_UNAVAILABLE"


def contextual_features(context, proposal):
    edits = proposal.edits
    start = edits[0].span.start.offset
    records = [row for row in context.nodes if enclosing(row.node.span, start)]
    node = records[-1].node if records else None
    scope = context.scope_at(start)
    replacement = edits[0].replacement.strip()
    name = re.fullmatch(r",?\s*([A-Za-z_][A-Za-z_0-9]*)", replacement)
    binding = context.visible_at(start).get(name[1]) if name else None
    writes = 0
    read_from_parameter = False
    if binding:
        for record in context.nodes:
            used = record.node
            if used.span.start.offset >= start:
                continue
            if isinstance(used, (Assignment, UpdateExpression)):
                target = used.target if isinstance(used, Assignment) else used.operand
                if isinstance(target, Identifier) and context.visible_at(target.span.start.offset).get(target.name) is binding:
                    writes += 1
            if used.span == binding.declaration_span:
                initializer = getattr(used, "initializer", None)
                if isinstance(initializer, Identifier):
                    origin = context.visible_at(initializer.span.start.offset).get(initializer.name)
                    read_from_parameter = bool(origin and origin.kind.value == "parameter")
    call = next((row.node for row in reversed(records) if isinstance(row.node, FunctionCall)), None)
    index_context = any(isinstance(row.node, ArrayAccess) for row in records)
    sign_similarity = 0.0
    if call and binding and isinstance(call.callee, Identifier):
        signature = context.visible_at(call.callee.span.start.offset).get(call.callee.name)
        fn = next((row.function for row in context.nodes if row.node is row.function
                   and signature and row.node.span == signature.declaration_span), None)
        if fn:
            position = next((i for i, arg in enumerate(call.arguments) if enclosing(arg.span, start)), len(call.arguments))
            if position < len(fn.parameters):
                sign_similarity = SequenceMatcher(None, fn.parameters[position].name, binding.name).ratio()
    return {
        "scope_kind": scope.kind.value if scope else "missing",
        "syntax_shape": type(node).__name__ if node else "missing",
        "is_function_local": int(scope is not None and scope.kind != ScopeKind.GLOBAL),
        "local_prior_updates": min(writes, 5), "initializer_reads_parameter": int(read_from_parameter),
        "argument_context": int(call is not None), "index_context": int(index_context),
        "formal_name_similarity": sign_similarity,
        "peer_support": min(sum(item.kind.startswith("ANALOGOUS") for item in proposal.evidence), 4),
        "insertion_count": sum(edit.span.start == edit.span.end for edit in edits),
        "deletion_count": sum(not edit.replacement for edit in edits),
    }
