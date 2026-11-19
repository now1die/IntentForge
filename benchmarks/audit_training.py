"""Measure template overlap with a reconstruction of the historical row split."""

import json
from collections import Counter

from sklearn.model_selection import train_test_split

from ai.dataset_generator import read_jsonl
from ai.feature_extraction import extract_features
from ai.scenario_training import _first_context

from .corpus import TRAINING_FILES, template_key, training_sources


def audit():
    rows = list(training_sources())
    train, test = train_test_split(rows, test_size=.20, random_state=42, stratify=[row[2] for row in rows])
    broken_templates = {template_key(row[0]) for row in train}
    fixed_templates = {template_key(row[1]) for row in train}

    literal_sources = {row[0] for row in train}
    features = Counter()
    labeled = [
        (row.error_context, row.label)
        for row in read_jsonl(TRAINING_FILES[0])
    ]
    with TRAINING_FILES[1].open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            labeled.append((_first_context(row["source"]), row["label"]))
    for context, label in labeled:
        strong_pattern = extract_features(context)["strong_pattern"]
        if strong_pattern != "NONE":
            features["named_pattern"] += 1
            if strong_pattern == label:
                features["matches_label"] += 1

    return {
        "archived_rows": len(rows),
        "archived_files": dict(zip((path.name for path in TRAINING_FILES),
                                   (sum(1 for row in training_sources((path,))) for path in TRAINING_FILES))),
        "split_seed": 42,
        "train_rows": len(train),
        "test_rows": len(test),
        "test_broken_template_seen_in_train": sum(template_key(row[0]) in broken_templates for row in test),
        "test_fixed_template_seen_in_train": sum(template_key(row[1]) in fixed_templates for row in test),
        "test_exact_broken_source_seen_in_train": sum(row[0] in literal_sources for row in test),
        "distinct_broken_templates": len({template_key(row[0]) for row in rows}),
        "distinct_fixed_templates": len({template_key(row[1]) for row in rows}),
        "features_audited": len(labeled),
        "strong_pattern_present": features["named_pattern"],
        "strong_pattern_equals_target": features["matches_label"],
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
