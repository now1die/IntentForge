"""Read versioned evaluation cases and check separation from archived model inputs."""

import json
from collections import Counter
from pathlib import Path

from compiler.lexer import tokenize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks" / "data"
TRAINING_FILES = (
    ROOT / "datasets" / "syntax_corrections.jsonl",
    ROOT / "datasets" / "adversarial_scenarios.jsonl",
)


def load_cases(directory: Path = DATA, *, corpus: str = "historical") -> list[dict]:
    cases = []
    if corpus not in {"historical", "holdout", "all"}:
        raise ValueError(f"Unknown corpus selection: {corpus}")
    files = []
    if corpus != "holdout":
        files.extend(sorted(directory.glob("*-v1.json")))
    if corpus != "historical":
        files.append(directory / "extended-v2.json")
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        expected_version = 2 if path.name == "extended-v2.json" else 1
        if data["version"] != expected_version or not isinstance(data["cases"], list):
            raise ValueError(f"Invalid corpus wrapper in {path}")
        cases.extend(data["cases"])
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("The evaluation corpus must have unique case IDs")
    family_splits = {}
    for case in cases:
        previous = family_splits.setdefault(case["mutation_family"], case["split"])
        if previous != case["split"] or case["split"] not in {"evaluation", "phase_1_5_holdout"}:
            raise ValueError(f"Unexpected split for family {case['mutation_family']}")
    return cases


def template_key(source: str) -> tuple[str, ...]:
    """Normalize identifiers and literals while keeping operators and bad tokens."""
    tokens, errors = tokenize(source)
    items = [(t.offset, t.type) for t in tokens]
    items.extend((e.span.start.offset, f"INVALID:{e.lexeme}") for e in errors)
    return tuple(kind for _, kind in sorted(items))


def training_sources(paths=TRAINING_FILES):
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    yield (
                        row.get("corrupted_source") or row["source"],
                        row.get("original_source") or row["expected_fix"],
                        row["label"],
                    )


def overlapping_cases(cases: list[dict], paths=TRAINING_FILES) -> list[str]:
    fingerprints = {template_key(source) for broken, fixed, _ in training_sources(paths) for source in (broken, fixed)}
    return [
        case["id"]
        for case in cases
        if any(template_key(source) in fingerprints for source in [case["source"], *case["acceptable_sources"]])
    ]


def near_duplicate_pairs(cases, paths=TRAINING_FILES, *, threshold=.88):
    """Screen normalized token four-grams against archive and corpus, in both directions."""
    def grams(key):
        return Counter(zip(key, key[1:], key[2:], key[3:]))

    archived = {
        template_key(source)
        for broken, fixed, _ in training_sources(paths) for source in (broken, fixed)
    }
    archive_signatures = [(f"archive-template-{i}", grams(key)) for i, key in enumerate(sorted(archived)) if len(key) >= 20]
    evaluated = [(case["id"], grams(key)) for case in cases if len(key := template_key(case["source"])) >= 20]
    pairs = []
    for i, (name, left) in enumerate(evaluated):
        left_total = left.total()
        for other, right in (*archive_signatures, *evaluated[:i]):
            right_total = right.total()
            if 2 * min(left_total, right_total) < threshold * (left_total + right_total):
                continue
            similarity = 2 * (left & right).total() / (left_total + right_total)
            if similarity >= threshold:
                pairs.append((name, other, round(similarity, 4)))
    return pairs
