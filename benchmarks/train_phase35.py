"""Fit structured v4 rankers and assess selective risk on separate families."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import joblib
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_learning import load_expanded_ranker
from ai.intention_uncertainty import classify
from ai.intention_v3_ranker import GeneralizedRanker, SCHEMA, V4_MODEL, load_generalized_ranker
from ai.correction_safety import repair_key

from .ml_v3_data import read
from .phase35_data import DEVELOPMENT
from .train_ml_v3 import fit, outcomes, risk, select

REPORT = DEVELOPMENT.parent.parent / "reports" / "phase35-training-v1.json"


def pool(rows):
    return [(row, analyze_intention(row["source"], phase35=True).candidates,
             {repair_key(text) for text in row["accepted"]}) for row in rows]


def policy_risk(rows, ranker):
    levels = Counter()
    errors = Counter()
    available = 0
    for row, choices, accepted in rows:
        order = order_candidates(choices, None, expanded=ranker, generalized=True)
        if order:
            available += 1
            top = order[0]
            decision = classify(top, ambiguous=len(order) > 1)
            tier = decision["tier"]
            levels[tier] += 1
            errors[tier] += repair_key(top.proposed_code) not in accepted
            if decision["recommendation"] == "REVIEW_WITH_EVIDENCE":
                levels["recommended"] += 1
                errors["recommended"] += repair_key(top.proposed_code) not in accepted
    return {"cases": len(rows), "cases_with_candidates": available, "levels": levels, "errors": errors}


def run():
    records = read(DEVELOPMENT)
    training, selection, calibration = [pool([row for row in records if row["split"] == split])
                                        for split in ("train", "selection", "calibration")]
    models, counts = fit(training)
    experimental = GeneralizedRanker(models, {})
    v2, v3 = load_expanded_ranker()[0], load_generalized_ranker()[0]
    repair_selection = [row for row in selection if row[2]]
    v2_rows, v3_rows = outcomes(repair_selection, v2), outcomes(repair_selection, v3)
    best_prior = [{**a, "top1": a["top1"] or b["top1"]} for a, b in zip(v2_rows, v3_rows, strict=True)]
    experiments = {name: outcomes(repair_selection, experimental, name) for name in models}
    deterministic = outcomes(repair_selection)
    activated, details = select({"deterministic": deterministic, "v2_on_v3_pool": best_prior, **experiments}, models)
    trainer = {"schema": SCHEMA, "models": models, "selected": activated}
    repair_calibration = [row for row in calibration if row[2]]
    return trainer, {
        "training": counts, "partitions": Counter(row["split"] for row in records), "selected": activated,
        "selection": details,
        "selection_top1": {key: [sum(row["top1"] for row in value), len(value)]
                           for key, value in {"deterministic": deterministic, "v2": v2_rows,
                                              "v3": v3_rows, **experiments}.items()},
        "calibration": {name: risk(outcomes(repair_calibration, experimental, name)) for name in models},
        "uncertainty_policy": policy_risk(calibration, GeneralizedRanker(models, activated)),
        "calibration_note": "Too few separated families and margin pairs for probabilities or category calibration.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=V4_MODEL)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    artifact, report = run()
    joblib.dump(artifact, args.model, compress=3)
    report["artifact_sha256"] = sha256(args.model.read_bytes()).hexdigest()
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["training"]))
