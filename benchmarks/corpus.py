"""Read versioned evaluation cases and check separation from archived model inputs."""

import json
from pathlib import Path

from compiler.lexer import tokenize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks" / "data"
TRAINING_FILES = (
    ROOT / "datasets" / "syntax_corrections.jsonl",
    ROOT / "datasets" / "adversarial_scenarios.jsonl",
)


def load_cases(directory: Path = DATA) -> list[dict]:
    cases = []
    for path in sorted(directory.glob("*-v1.json")):
        corpus = json.loads(path.read_text(encoding="utf-8"))
        if corpus["version"] != 1:
            raise ValueError(f"Unsupported corpus version in {path}")
        cases.extend(corpus["cases"])
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("The evaluation corpus must have unique case IDs")
    family_splits = {}
    for case in cases:
        previous = family_splits.setdefault(case["mutation_family"], case["split"])
        if previous != case["split"] or case["split"] != "evaluation":
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
