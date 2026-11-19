"""Train and review category-local ranking effects on held-out families."""

import argparse
from collections import defaultdict
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ai.correction_safety import repair_key
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_learning import FEATURE_VERSION, ExpandedRanker, MODEL_PATH, difference
from ai.intention_ranker import load_ranker

from .corpus import ROOT
from .phase25_data import DEVELOPMENT, SEED


REPORT = ROOT / "benchmarks" / "reports" / "phase25-training-v1.json"


def examples(data):
    for case in data:
        result = analyze_intention(case["source"], enhanced=True)
        accepted = {repair_key(source) for source in case["accepted"]}
        labels = {cand.id for cand in result.candidates if repair_key(cand.proposed_code) in accepted}
        yield case, result.candidates, labels


def make_models(training):
    features, labels, pairs, pair_labels = [], [], [], []
    for case, candidates, positives in training:
        if case.get("ambiguous"):
            continue
        features.extend(c.features for c in candidates)
        labels.extend(int(c.id in positives) for c in candidates)
        for p in candidates:
            if p.id not in positives:
                continue
            for n in candidates:
                if n.id not in positives and n.proposal.category == p.proposal.category:
                    pairs.extend([difference(p.features, n.features), difference(n.features, p.features)])
                    pair_labels.extend([1, 0])
    models = {
        "pointwise": Pipeline([("features", DictVectorizer()), ("ranker", LogisticRegression(C=1, class_weight="balanced", random_state=SEED))]),
        "pairwise": Pipeline([("features", DictVectorizer()), ("ranker", LogisticRegression(C=1, random_state=SEED))]),
        "boosted": Pipeline([("features", DictVectorizer(sparse=False)), ("ranker", GradientBoostingClassifier(
            n_estimators=40, max_depth=2, random_state=SEED,
        ))]),
    }
    elapsed = {}
    for name, model in models.items():
        start = perf_counter()
        model.fit(pairs if name == "pairwise" else features, pair_labels if name == "pairwise" else labels)
        elapsed[name] = (perf_counter() - start) * 1000
    return models, {"rows": len(labels), "positive_rows": sum(labels), "pair_rows": len(pair_labels), "fit_ms": elapsed}


def measure(rows, models, method, v1=None, *, selected=None):
    output = []
    expanded = ExpandedRanker(models, selected or {})
    for case, candidates, accepted in rows:
        ordered = order_candidates(candidates, v1 if method == "phase2" else None,
                                   expanded=expanded if method in {*models, "selected"} else None,
                                   experimental=method if method in models else None)
        winner = ordered[0] if ordered else None
        margins = [c.relative_score for c in ordered[1:] if c.relative_score is not None
                   and winner and c.proposal.category == winner.proposal.category
                   and c.compiler_valid == winner.compiler_valid
                   and c.remaining_diagnostics == winner.remaining_diagnostics]
        margin = winner.relative_score - max(margins) if winner and winner.relative_score is not None and margins else None
        output.append({"id": case["id"], "family": case["family"], "category": case["category"],
                       "top1": bool(winner and winner.id in accepted),
                       "top3": any(c.id in accepted for c in ordered[:3]), "recall": bool(accepted),
                       "margin": margin, "ambiguous": bool(case.get("ambiguous"))})
    return output


def summarise(rows):
    groups = defaultdict(list)
    for row in rows:
        if not row["ambiguous"]:
            groups[row["category"]].append(row)
    result = {}
    for category, values in groups.items():
        family = defaultdict(list)
        for row in values:
            family[row["family"]].append(row["top1"])
        result[category] = {
            "cases": len(values), "families": len(family), "top1": sum(r["top1"] for r in values),
            "top3": sum(r["top3"] for r in values), "recall": sum(r["recall"] for r in values),
            "macro_top1": mean(mean(hits) for hits in family.values()),
        }
    return result


def calibrate(validation, held):
    fit = [row for row in validation if row["margin"] is not None and not row["ambiguous"]]
    check = [row for row in held if row["margin"] is not None and not row["ambiguous"]]
    report = {"fit_cases": len(fit), "heldout_cases": len(check), "exposed_probabilities": False}
    if not fit or not check or len({r["top1"] for r in fit}) < 2:
        return {**report, "reason": "Insufficient margin and outcome diversity"}
    x = [[r["margin"]] for r in fit]
    y = [int(r["top1"]) for r in fit]
    test = [[r["margin"]] for r in check]
    target = np.array([int(r["top1"]) for r in check])
    sigmoid = LogisticRegression().fit(x, y)
    isotonic = IsotonicRegression(out_of_bounds="clip").fit(np.ravel(x), y)
    probabilities = {"prevalence": np.full(len(test), mean(y)), "sigmoid": sigmoid.predict_proba(test)[:, 1],
                     "isotonic": isotonic.predict(np.ravel(test))}
    report["heldout_families"] = len({r["family"] for r in check})
    report["brier"] = {key: float(np.mean((values-target)**2)) for key, values in probabilities.items()}
    report["risk_coverage"] = []
    ranked = sorted(check, key=lambda row: (-row["margin"], row["id"]))
    for coverage in (.25, .5, .75, 1.0):
        k = max(1, round(len(ranked)*coverage))
        active = ranked[:k]
        report["risk_coverage"].append({"covered": k, "total": len(ranked),
                                        "incorrect": sum(not row["top1"] for row in active),
                                        "minimum_margin": active[-1]["margin"]})
    report["reason"] = "Sparse synthetic family support and unverified runtime behavior."
    return report


def train(data):
    groups = defaultdict(list)
    for case, candidates, labels in examples(data["cases"]):
        groups[case["split"]].append((case, candidates, labels))
    models, counts = make_models(groups["train"])
    v1, _ = load_ranker()
    methods = ["deterministic", "phase2", *models]
    results = {method: summarise(measure(groups["validation"], models, method, v1)) for method in methods}
    selected = {}
    for category, baseline in results["deterministic"].items():
        best = max(models, key=lambda method: (results[method][category]["macro_top1"],
                                               results[method][category]["top1"], method == "pointwise"))
        measured = results[best][category]
        legacy = results["phase2"][category]
        if (baseline["families"] >= 2 and measured["top1"] > max(baseline["top1"], legacy["top1"])
                and measured["macro_top1"] > max(baseline["macro_top1"], legacy["macro_top1"])):
            selected[category] = best
    val = measure(groups["validation"], models, "selected", selected=selected)
    held = measure(groups["calibration"], models, "selected", selected=selected)
    # When deployment is rejected, still assess calibration of the strongest
    # preselected experimental ranking on separate families.
    cal_method = "selected" if selected else max(models, key=lambda name: sum(item["top1"] for item in results[name].values()))
    if not selected:
        val = measure(groups["validation"], models, cal_method)
        held = measure(groups["calibration"], models, cal_method)
    artifact = {"feature_version": FEATURE_VERSION, "models": models, "selected": selected}
    report = {
        **counts, "seed": SEED, "selected": selected, "validation": results,
        "calibration": {"method_under_assessment": cal_method,
                        "pooled_exploratory": calibrate(val, held),
                        "by_category": {category: calibrate(
                            [row for row in val if row["category"] == category],
                            [row for row in held if row["category"] == category])
                            for category in results["deterministic"]}},
        "development": {method: summarise(measure(groups["development"], models, method, v1, selected=selected))
                        for method in [*methods, "selected"]},
        "groups": {split: {"cases": len(rows), "families": len({case["family"] for case, _, _ in rows})}
                   for split, rows in groups.items()},
        "environment": {name: version(name) for name in ("scikit-learn", "numpy", "joblib")},
        "hyperparameters": {name: model.named_steps["ranker"].get_params() for name, model in models.items()},
    }
    return artifact, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    data = DEVELOPMENT.read_bytes()
    artifact, report = train(json.loads(data))
    joblib.dump(artifact, args.model, compress=3)
    report["development_sha256"] = sha256(data).hexdigest()
    report["artifact_sha256"] = sha256(args.model.read_bytes()).hexdigest()
    report["artifact_bytes"] = args.model.stat().st_size
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(report["selected"], report["groups"], report["calibration"])
