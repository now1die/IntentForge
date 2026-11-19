"""Context-aware pointwise ranking of already validated local alternatives."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline


FEATURE_VERSION = 1
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "intention_ranker_v1.joblib"


@dataclass(frozen=True, slots=True)
class Ranker:
    pipeline: Pipeline
    version: str

    def score(self, rows):
        return [float(value) for value in self.pipeline.decision_function(rows)]


@lru_cache(maxsize=1)
def load_ranker(path: Path = MODEL_PATH) -> tuple[Ranker | None, str]:
    """Load a repository-owned artifact. Requests cannot specify artifact paths."""
    try:
        artifact = joblib.load(path)
        if artifact["feature_version"] != FEATURE_VERSION or not isinstance(artifact["model"], Pipeline):
            return None, "ARTIFACT_INCOMPATIBLE"
        if not artifact["enabled"]:
            return None, "VALIDATION_GATE_NOT_MET"
        return Ranker(artifact["model"], artifact["version"]), "LEARNED"
    except Exception:
        return None, "ARTIFACT_UNAVAILABLE"
