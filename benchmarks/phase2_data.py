"""Construct the Phase 2 ranker's family-separated development corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random

from .corpus import DATA


SEED = 2081
DEVELOPMENT = DATA / "phase2-development-v1.json"
FINAL = DATA / "phase2-evaluation-v1.json"

# Each generator starts with a reference program and mutates one binding use.
# Typo spelling deliberately favors the decoy in many cases, so contextual use matters.
FAMILIES = {
    "train": {
        "accumulate_then_report": "int {f}(int {p}){{int {good}={p}+{n}; int {bad}=1; {good}+=2; return {good};}}",
        "branch_then_update": "int {f}(int {p}, bool enabled){{int {good}={p}; int {bad}=8; if(enabled){{{good}+=3;}} {good}*=2; return {good};}}",
        "bounded_while": "int {f}(int {p}){{int {good}={p}; int {bad}=9; while({good}<{n}){{{good}++;}} return {good};}}",
        "computed_global_array_lookup": "int data_{f}[8]; int {f}(int {p}){{int {good}=data_{f}[{p}]; int {bad}=2; {good}+=data_{f}[0]; return {good};}}",
        "condition_then_for": "int {f}(int {p}){{int {good}={p}; int {bad}=1; for(int k=0;k<{n};k++){{if(k>1){{{good}+=k;}}}} return {good};}}",
        "branch_with_char_decoy": "int {f}(int {p}){{int {good}={p}*2; char {bad}='a'; if({good}>9){{{good}--;}} return {good};}}",
        "call_and_adjust": "int twice_{f}(int x){{return x*2;}} int {f}(int {p}){{int {good}=twice_{f}({p});int {bad}=4; {good}-={n};return {good};}}",
        "reused_argument": "int {f}(int {good},int {p}){{int {bad}={p}+{n};if({good}>1){{{good}+=4;}}{good}-=2;return {good};}}",
        "temporary_scope": "int {f}(int {p}){{int {good}={p};int {bad}=2;{{int local={n};{good}+=local;}}return {good};}}",
        "conditional_decoy_used": "int {f}(int {p}){{int {good}={p};int {bad}={n}; if({bad}==0){{return 0;}} {good}*=3;{good}+=1;return {good};}}",
    },
    "validation": {
        "loop_with_break_and_update": "int {f}(int {p}){{int {good}=0;int {bad}=3;while({p}>0){{if({good}>8){{break;}}{good}+={p};{p}--;}}return {good};}}",
        "array_aggregate_early_return": "int cells_{f}[5]; int {f}(int {p}){{int {good}=cells_{f}[{p}];int {bad}=1;if({good}<{n}){{return 0;}}{good}+=cells_{f}[1];return {good};}}",
        "separate_helper_and_branch": "int bump_{f}(int x,int y){{return x+y;}} int {f}(int {p},bool ok){{int {good}=bump_{f}({p},{n});int {bad}=7;if(ok){{{good}*=2;}}else{{{good}-=1;}}return {good};}}",
        "reuse_inside_nested_loop": "int {f}(int {p}){{int {good}={p};int {bad}=2;for(int a=0;a<3;a++){{for(int b=0;b<2;b++){{{good}+=a*b;}}}}return {good};}}",
        "parameters_and_early_exit": "int {f}(int {good}, int {p}, bool stop){{int {bad}={p};if(stop){{return {p};}}{good}+={n};{good}*=2;return {good};}}",
    },
}

NAMES = (
    ("subtotal", "address", "addres"),
    ("running", "moment", "momnt"),
    ("reading", "capacity", "capacit"),
    ("combined", "position", "postion"),
    ("estimate", "padding", "paddng"),
    ("measured", "threshold", "thresold"),
    ("result", "interval", "intervl"),
    ("quantity", "marker", "markr"),
    ("balance", "shadow", "shado"),
    ("progress", "previous", "progres"),
)


def generate():
    random = Random(SEED)
    cases = []
    for split, families in FAMILIES.items():
        for family, template in families.items():
            for index, (good, bad, broken) in enumerate(NAMES):
                identity = f"{family}_{index}"
                reference = template.format(f=identity, p="value", good=good, bad=bad, n=random.randrange(2, 18))
                before, tail = reference.rsplit(f"return {good};", 1)
                cases.append({
                    "id": identity, "family": family, "split": split,
                    "provenance": "P2_AI_ASSISTED_REFERENCE_MUTATION",
                    "source": before + f"return {broken};" + tail,
                    "accepted": reference,
                })
    return {"version": 1, "seed": SEED, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEVELOPMENT)
    args = parser.parse_args()
    args.out.write_text(json.dumps(generate(), indent=2) + "\n")
