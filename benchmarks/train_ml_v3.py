"""Train and select v3 rankers using only the development corpus."""
import argparse
from collections import Counter, defaultdict
import json
from math import comb
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from ai.correction_safety import repair_key
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_generalization import evidence_strength
from ai.intention_learning import difference, load_expanded_ranker
from ai.intention_v3_ranker import GeneralizedRanker, MODEL, SCHEMA, eligible, learned_fields

from .corpus import ROOT
from .ml_v3_data import DEVELOPMENT, read

REPORT = ROOT / "benchmarks/reports/ml-v3-training-v1.json"
SEED = 7019


def pools(rows):
    return [(case, analyze_intention(case["source"], generalized=True, budget_seconds=5).candidates,
             {repair_key(text) for text in case["accepted"]}) for case in rows if case["accepted"]]


def fit(train):
    point_rows, point_labels, pair_rows, pair_labels = [], [], [], []
    for _, choices, accepted in train:
        strata = defaultdict(list)
        for candidate in choices:
            if not eligible(candidate):
                continue
            strata[(candidate.proposal.category, candidate.compiler_valid, candidate.remaining_diagnostics,
                    evidence_strength(candidate.proposal))].append(
                (learned_fields(candidate), int(repair_key(candidate.proposed_code) in accepted)))
        for group in strata.values():
            if len(group) < 2 or len({label for _, label in group}) < 2:
                continue
            for row, label in group:
                point_rows.append(row)
                point_labels.append(label)
            for positive, _ in (item for item in group if item[1]):
                for negative, _ in (item for item in group if not item[1]):
                    pair_rows.extend([difference(positive, negative), difference(negative, positive)])
                    pair_labels.extend([1, 0])
    models = {
        "pointwise": make_pipeline(DictVectorizer(), LogisticRegression(class_weight="balanced", random_state=SEED)),
        "pairwise": make_pipeline(DictVectorizer(), LogisticRegression(random_state=SEED)),
        "boosted": make_pipeline(DictVectorizer(sparse=False),
                                 GradientBoostingClassifier(n_estimators=35, max_depth=2, random_state=SEED)),
    }
    for name, model in models.items():
        model.fit(pair_rows, pair_labels) if name == "pairwise" else model.fit(point_rows, point_labels)
    return models, {"point_rows": len(point_rows), "point_positives": sum(point_labels), "pair_rows": len(pair_rows)}


def outcomes(rows, ranker=None, method=None):
    output = []
    for case, choices, accepted in rows:
        order = order_candidates(choices, None, expanded=ranker, experimental=method, generalized=True)
        win = bool(order and repair_key(order[0].proposed_code) in accepted)
        margin = None
        if len(order) > 1 and all(item.relative_score is not None for item in order[:2]):
            a, b = order[:2]
            if a.proposal.category == b.proposal.category and a.compiler_valid == b.compiler_valid:
                margin = a.relative_score - b.relative_score
        output.append({"id": case["id"], "category": case["category"], "family": case["family"],
                       "top1": win, "margin": margin,
                       "strong": bool(order and evidence_strength(order[0].proposal))})
    return output


def select(results, methods):
    selected, detail = {}, {}
    for category in sorted({row["category"] for row in results["deterministic"]}):
        by_method = {name: {row["family"]: row["top1"] for row in rows if row["category"] == category}
                     for name, rows in results.items()}
        det, v2 = by_method["deterministic"], by_method["v2_on_v3_pool"]
        evidence = {}
        for name in methods:
            current = by_method[name]
            wins = sum(value and not (det[family] or v2[family]) for family, value in current.items())
            losses = sum(not value and (det[family] or v2[family]) for family, value in current.items())
            n = wins + losses
            p = sum(comb(n, i) for i in range(wins, n + 1)) / (2 ** n)
            evidence[name] = {"wins_over_either_baseline": wins, "losses": losses, "sign_test_p": p}
        candidates = [name for name in methods if evidence[name]["wins_over_either_baseline"] >= 3
                      and evidence[name]["losses"] == 0 and evidence[name]["sign_test_p"] <= .125]
        if candidates:
            selected[category] = min(candidates, key=lambda name: evidence[name]["sign_test_p"])
        detail[category] = {"families": len(det), "top1": {name: sum(rows.values()) for name, rows in by_method.items()},
                            "evidence": evidence}
    return selected, detail


def risk(rows):
    margin_rows = sorted((row for row in rows if row["margin"] is not None), key=lambda row: -row["margin"])
    return {"ranked_margin_coverage": [len(margin_rows), len(rows)], "selection_risk": [
            {"retained": count, "errors": sum(not row["top1"] for row in margin_rows[:count])}
            for count in sorted({1, (len(margin_rows) + 1) // 2, len(margin_rows)}) if 0 < count <= len(margin_rows)],
            "evidence_strata": {name: {"count": len(bucket), "errors": sum(not row["top1"] for row in bucket)}
                                for name, bucket in [("strong", [row for row in rows if row["strong"]]),
                                                     ("other", [row for row in rows if not row["strong"]])]}}


def run():
    records = read(DEVELOPMENT)
    train, validation, calibration = [pools([case for case in records if case["split"] == split])
                                     for split in ("train", "selection", "calibration")]
    models, counts = fit(train)
    tester = GeneralizedRanker(models, {})
    phase25 = load_expanded_ranker()[0]
    selection = {"deterministic": outcomes(validation), "v2_on_v3_pool": outcomes(validation, phase25)}
    selection.update({name: outcomes(validation, tester, name) for name in models})
    selected, evidence = select(selection, models)
    calibration_results = {"deterministic": risk(outcomes(calibration))}
    calibration_results.update({name: risk(outcomes(calibration, tester, name)) for name in models})
    return {"schema": SCHEMA, "models": models, "selected": selected}, {
        "seed": SEED, "partition_counts": Counter(row["split"] for row in records), "training": counts,
        "selection": evidence, "selected": selected, "calibration": calibration_results,
        "probability_calibration": "Unavailable. Margin-scored labels and independent families are insufficient.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    artifact, report = run()
    joblib.dump(artifact, args.model, compress=3)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"training": report["training"], "selected": report["selected"]}))
