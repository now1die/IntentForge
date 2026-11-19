"""Versioned structured ranking with per-category activation."""
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path
from time import monotonic

import joblib
from sklearn.pipeline import Pipeline

from .intention_generalization import evidence_strength
from .intention_learning import difference


MODEL = Path(__file__).resolve().parents[1] / "models" / "intention_ranker_v3.joblib"
SCHEMA = 1
# These textual similarities and rule hints are useful audit fields, but
# are deliberately excluded from the learned scores.
EXCLUDED = {"identifier_similarity", "formal_name_similarity", "symbol_distance",
            "strong_evidence", "peer_evidence", "peer_support", "has_requirement_support"}


def learned_fields(candidate):
    return {key: value for key, value in candidate.features.items() if key not in EXCLUDED}


def eligible(candidate):
    return any(fact.kind == "COMPILER_DIAGNOSTIC" for fact in candidate.proposal.evidence)


@dataclass(frozen=True)
class GeneralizedRanker:
    models: dict
    selected: dict

    def order(self, group, *, experimental=None, deadline=None):
        slots = {}
        for index, candidate in enumerate(group):
            if eligible(candidate):
                slots.setdefault((candidate.proposal.category, evidence_strength(candidate.proposal)), []).append(index)
        result = list(group)
        for (category, _), indices in slots.items():
            method = experimental or self.selected.get(category)
            if len(indices) < 2 or method not in self.models:
                continue
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Ranking deadline exceeded")
            candidates = [group[index] for index in indices]
            rows = [learned_fields(item) for item in candidates]
            model = self.models[method]
            if method == "pairwise":
                pairs = [(i, difference(a, b)) for i, a in enumerate(rows) for j, b in enumerate(rows) if i != j]
                scores = [0.0] * len(rows)
                for (i, _), value in zip(pairs, model.decision_function([row for _, row in pairs]), strict=True):
                    scores[i] += float(value) / (len(rows) - 1)
            else:
                scores = model.decision_function(rows)
            if deadline is not None and monotonic() >= deadline:
                raise TimeoutError("Ranking deadline exceeded")
            for item, value in zip(candidates, scores, strict=True):
                if not isfinite(value):
                    raise ValueError("Nonfinite rank margin")
                item.relative_score = float(value)
            for i, item in zip(indices, sorted(candidates, key=lambda item: -item.relative_score), strict=True):
                result[i] = item
        return result


@lru_cache(maxsize=1)
def load_generalized_ranker():
    try:
        if MODEL.stat().st_size > 2_000_000:
            raise ValueError("Ranker exceeds artifact budget")
        artifact = joblib.load(MODEL)
        models, selected = artifact["models"], artifact["selected"]
        if (artifact["schema"] != SCHEMA or not isinstance(selected, dict)
                or not all(isinstance(model, Pipeline) for model in models.values())
                or not all(method in models for method in selected.values())):
            raise ValueError("Incompatible ranker artifact")
    except Exception:
        return None, "V3_ARTIFACT_UNAVAILABLE"
    return GeneralizedRanker(models, selected), "V3_LEARNED" if selected else "V3_DETERMINISTIC"
