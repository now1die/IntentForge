"""Fit pointwise ranking on development families and gate activation on validation."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter
import argparse
import platform
from importlib.metadata import version
from statistics import mean

import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ai.correction_safety import repair_key
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_ranker import FEATURE_VERSION, MODEL_PATH, Ranker

from .corpus import ROOT
from .phase2_data import DEVELOPMENT, SEED


def development_rankings(cases):
    sets = {"train": [], "validation": []}
    for case in cases:
        candidates = analyze_intention(case["source"]).candidates
        labels = {item.id for item in candidates if repair_key(item.proposed_code) == repair_key(case["accepted"])}
        sets[case["split"]].append((case["family"], candidates, labels))
    return sets


def validation_metrics(rows, ranker=None):
    families = defaultdict(list)
    top3 = recall = pairs = ordered_pairs = 0
    scores_ms = []
    for family, candidates, labels in rows:
        start = perf_counter()
        ordered = order_candidates(candidates, ranker)
        scores_ms.append((perf_counter() - start) * 1000)
        identifiers = [item.id for item in ordered]
        hit = bool(identifiers and identifiers[0] in labels)
        top3 += any(identifier in labels for identifier in identifiers[:3])
        recall += bool(labels)
        for i, item in enumerate(identifiers):
            if item in labels:
                negatives = [j for j, other in enumerate(identifiers) if other not in labels]
                pairs += len(negatives)
                ordered_pairs += sum(i < j for j in negatives)
        families[family].append(hit)
    return {
        "top_1": sum(sum(values) for values in families.values()), "top_3": top3,
        "cases": len(rows), "candidate_recall": recall,
        "pairs_ordered": ordered_pairs, "pairs": pairs,
        "family_macro_top_1": mean(mean(values) for values in families.values()),
        "case_ranking_mean_ms": mean(scores_ms),
    }


def fit(development):
    sets = development_rankings(development["cases"])
    train = sets["train"]
    valid = sets["validation"]
    feature_rows = [item.features for _, choices, _ in train for item in choices]
    labels = [item.id in accepted for _, choices, accepted in train for item in choices]
    measurements = {"deterministic": validation_metrics(valid)}
    baseline = measurements["deterministic"]
    choices = {
        "logistic": LogisticRegression(C=1.0, class_weight="balanced", random_state=SEED),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=40, max_depth=2, random_state=SEED),
    }
    trained = {}
    for name, estimator in choices.items():
        for _, candidates, _ in valid:
            for item in candidates:
                item.relative_score = None
        pipeline = Pipeline([("vector", DictVectorizer(sparse=name == "logistic")), ("ranker", estimator)])
        start = perf_counter()
        pipeline.fit(feature_rows, labels)
        elapsed = (perf_counter() - start) * 1000
        ranker = Ranker(pipeline, f"intention-v1-{name}")
        measurements[name] = {**validation_metrics(valid, ranker), "fit_ms": elapsed,
                              "hyperparameters": estimator.get_params()}
        trained[name] = ranker
    winner = max(choices, key=lambda name: (measurements[name]["family_macro_top_1"],
                                                   measurements[name]["pairs_ordered"], name == "logistic"))
    selected = trained[winner]
    metrics = measurements[winner]
    enabled = metrics["top_1"] > baseline["top_1"] and metrics["family_macro_top_1"] > baseline["family_macro_top_1"]
    artifact = {"feature_version": FEATURE_VERSION, "version": selected.version,
                "enabled": enabled, "model": selected.pipeline}
    report = {
        "selected": winner, "enabled": enabled, "model_version": selected.version,
        "selection_gate": "Both validation top-1 count and family-macro top-1 exceed deterministic ranking.",
        "seed": SEED, "train_cases": len(train), "validation_cases": len(valid),
        "train_candidates": len(labels), "positive_candidates": sum(labels),
        "feature_names": selected.pipeline.named_steps["vector"].feature_names_,
        "measurements": measurements,
        "environment": {"python": platform.python_version(), **{package: version(package) for package in ("scikit-learn", "numpy", "joblib")}},
    }
    return artifact, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--report", type=Path, default=ROOT / "benchmarks" / "reports" / "phase2-training-v1.json")
    args = parser.parse_args()
    raw = DEVELOPMENT.read_bytes()
    artifact, report = fit(json.loads(raw))
    joblib.dump(artifact, args.model, compress=3)
    report["development_sha256"] = sha256(raw).hexdigest()
    report["artifact_sha256"] = sha256(args.model.read_bytes()).hexdigest()
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['model_version']}, deployment gate: {report['enabled']}; report {args.report}")
